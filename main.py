import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from worker_pool import (
    WORKER_POOL_SIZE,
    enqueue_task,
    enqueue_task_after_delay,
    start_worker_pool,
    stop_worker_pool,
    task_db,
    task_events,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    workers = start_worker_pool(WORKER_POOL_SIZE)
    yield
    stop_worker_pool(workers)


app = FastAPI(lifespan=lifespan)


@app.post("/tasks/run-now")
async def create_immediate_task(prompt: str):
    task_id = str(uuid.uuid4())[:8]
    await enqueue_task(task_id, prompt)
    return {"message": "메시지 큐에 등록되었습니다.", "task_id": task_id}


@app.post("/tasks/schedule")
async def create_scheduled_task(prompt: str, delay_seconds: int):
    task_id = str(uuid.uuid4())[:8]
    run_time = datetime.now() + timedelta(seconds=delay_seconds)
    task_db[task_id] = {
        "status": f"SCHEDULED ({run_time.strftime('%H:%M:%S')})",
        "worker": None,
        "result": None,
    }
    task_events[task_id] = asyncio.Event()

    asyncio.create_task(enqueue_task_after_delay(delay_seconds, task_id, prompt))
    return {
        "message": f"{delay_seconds}초 뒤에 큐로 전달되도록 예약되었습니다.",
        "task_id": task_id,
        "scheduled_time": run_time,
    }


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    return task_db.get(task_id, {"error": "존재하지 않는 작업 ID입니다."})


# 폴링 없이 작업 완료 시점까지 대기했다가 결과를 푸시(Push)하는 SSE 엔드포인트
@app.get("/tasks/{task_id}/stream")
async def stream_task_result(task_id: str):
    if task_id not in task_db:
        return {"error": "존재하지 않는 작업 ID입니다."}

    async def event_generator():
        # 아직 완료되지 않았다면 워커의 event.set() 신호가 올 때까지 유휴 대기 (Polling 0회)
        if task_db[task_id]["status"] != "COMPLETED":
            await task_events[task_id].wait()

        payload = json.dumps(task_db[task_id], ensure_ascii=False)
        yield f"data: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health_check():
    return {"status": "ok", "active_workers": WORKER_POOL_SIZE}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
