import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import uvicorn
from fastapi import FastAPI

from worker_pool import (
    WORKER_POOL_SIZE,
    enqueue_task,
    enqueue_task_after_delay,
    start_worker_pool,
    stop_worker_pool,
    task_db,
)


# 서버 시작 시 워커 풀 가동 및 종료 시 정리
@asynccontextmanager
async def lifespan(app: FastAPI):
    workers = start_worker_pool(WORKER_POOL_SIZE)
    yield
    stop_worker_pool(workers)


app = FastAPI(lifespan=lifespan)


# 1. 즉시 실행 요청 API
@app.post("/tasks/run-now")
async def create_immediate_task(prompt: str):
    task_id = str(uuid.uuid4())[:8]
    await enqueue_task(task_id, prompt)
    return {"message": "메시지 큐에 등록되었습니다.", "task_id": task_id}


# 2. 지연 스케줄링 요청 API
@app.post("/tasks/schedule")
async def create_scheduled_task(prompt: str, delay_seconds: int):
    task_id = str(uuid.uuid4())[:8]
    run_time = datetime.now() + timedelta(seconds=delay_seconds)
    task_db[task_id] = {
        "status": f"SCHEDULED ({run_time.strftime('%H:%M:%S')})",
        "worker": None,
        "result": None,
    }

    asyncio.create_task(enqueue_task_after_delay(delay_seconds, task_id, prompt))
    return {
        "message": f"{delay_seconds}초 뒤에 큐로 전달되도록 예약되었습니다.",
        "task_id": task_id,
        "scheduled_time": run_time,
    }


# 3. 작업 상태 및 담당 워커 조회 API
@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    return task_db.get(task_id, {"error": "존재하지 않는 작업 ID입니다."})


# 4. 헬스체크 API
@app.get("/health")
async def health_check():
    return {"status": "ok", "active_workers": WORKER_POOL_SIZE}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
