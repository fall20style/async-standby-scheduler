import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import uvicorn
from fastapi import FastAPI

# 1. 이벤트 기반 비동기 메시지 큐 & 상태 저장소
task_queue: asyncio.Queue = asyncio.Queue()
task_db: dict = {}
WORKER_POOL_SIZE = 3  # 동시에 작업을 처리할 워커 풀 크기


# 2. 워커 풀에서 대기하며 메시지를 받아 처리하는 워커 코루틴
async def worker(worker_name: str):
    print(f"[{datetime.now()}] [{worker_name}] 준비 완료 (이벤트 대기 중...)")
    while True:
        # 폴링(sleep) 없이 메시지가 들어올 때까지 이벤트 루프에서 대기
        task_id, prompt = await task_queue.get()

        try:
            task_db[task_id]["status"] = "RUNNING"
            task_db[task_id]["worker"] = worker_name
            print(f"[{datetime.now()}] [{worker_name}] 작업 시작 ({task_id}): {prompt}")

            # 시간이 걸리는 AI 작업 시뮬레이션 (5초)
            await asyncio.sleep(5)

            if prompt.strip().lower() == "hello":
                output = "HELLO WORLD"
            else:
                output = f"'{prompt}'에 대한 요약 보고서 생성 완료"

            task_db[task_id]["status"] = "COMPLETED"
            task_db[task_id]["result"] = output
            print(f"[{datetime.now()}] [{worker_name}] 출력 결과 ({task_id}): {output}")
            print(f"[{datetime.now()}] [{worker_name}] 작업 완료 ({task_id})")
        finally:
            # 큐에 작업 완료 신호 전달
            task_queue.task_done()


# 3. 서버 시작 시 워커 풀 생성 및 종료 시 정리
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 지정된 개수만큼 워커를 생성해 풀(Pool)로 가동
    workers = [
        asyncio.create_task(worker(f"Worker-{i+1}"))
        for i in range(WORKER_POOL_SIZE)
    ]
    yield
    # 서버 종료 시 실행 중인 워커 태스크 취소
    for w in workers:
        w.cancel()


app = FastAPI(lifespan=lifespan)


# 지연 시간 후 큐에 메시지를 넣는 헬퍼 함수
async def enqueue_after_delay(delay_seconds: int, task_id: str, prompt: str):
    await asyncio.sleep(delay_seconds)
    task_db[task_id]["status"] = "QUEUED"
    await task_queue.put((task_id, prompt))


# 4. 즉시 실행 API (큐에 넣자마자 대기 중인 워커가 즉시 깨어나 처리)
@app.post("/tasks/run-now")
async def create_immediate_task(prompt: str):
    task_id = str(uuid.uuid4())[:8]
    task_db[task_id] = {"status": "QUEUED", "worker": None, "result": None}

    # 큐에 메시지 삽입 (즉시 이벤트 발생)
    await task_queue.put((task_id, prompt))
    return {"message": "메시지 큐에 등록되었습니다.", "task_id": task_id}


# 5. 스케줄링 실행 API
@app.post("/tasks/schedule")
async def create_scheduled_task(prompt: str, delay_seconds: int):
    task_id = str(uuid.uuid4())[:8]
    run_time = datetime.now() + timedelta(seconds=delay_seconds)
    task_db[task_id] = {
        "status": f"SCHEDULED ({run_time.strftime('%H:%M:%S')})",
        "worker": None,
        "result": None,
    }

    # 타이머 이벤트 등록 (지연 시간 경과 후 큐에 삽입)
    asyncio.create_task(enqueue_after_delay(delay_seconds, task_id, prompt))
    return {
        "message": f"{delay_seconds}초 뒤에 큐로 전달되도록 예약되었습니다.",
        "task_id": task_id,
        "scheduled_time": run_time,
    }


# 6. 상태 및 담당 워커 조회 API
@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    return task_db.get(task_id, {"error": "존재하지 않는 작업 ID입니다."})


@app.get("/health")
async def health_check():
    return {"status": "ok", "active_workers": WORKER_POOL_SIZE}


if __name__ == "__main__":
    uvicorn.run("worker_pool:app", host="127.0.0.1", port=8000, reload=True)
