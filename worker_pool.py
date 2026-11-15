import asyncio
from datetime import datetime

# 전역 변수는 None으로 선언하고, 워커 풀 시작 시 현재 이벤트 루프에 맞춰 생성
task_queue: asyncio.Queue | None = None
task_db: dict = {}
WORKER_POOL_SIZE = 3


async def worker(worker_name: str):
    print(f"[{datetime.now()}] [{worker_name}] 준비 완료 (이벤트 대기 중...)")
    while True:
        task_id, prompt = await task_queue.get()
        try:
            task_db[task_id]["status"] = "RUNNING"
            task_db[task_id]["worker"] = worker_name
            print(f"[{datetime.now()}] [{worker_name}] 작업 시작 ({task_id}): {prompt}")

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
            task_queue.task_done()


def start_worker_pool(pool_size: int = WORKER_POOL_SIZE) -> list[asyncio.Task]:
    global task_queue
    # 현재 실행 중인 이벤트 루프에 바인딩된 새 큐와 DB 초기화
    task_queue = asyncio.Queue()
    task_db.clear()
    return [
        asyncio.create_task(worker(f"Worker-{i + 1}"))
        for i in range(pool_size)
    ]


def stop_worker_pool(workers: list[asyncio.Task]):
    for w in workers:
        w.cancel()


async def enqueue_task(task_id: str, prompt: str):
    task_db[task_id] = {"status": "QUEUED", "worker": None, "result": None}
    await task_queue.put((task_id, prompt))


async def enqueue_task_after_delay(delay_seconds: int, task_id: str, prompt: str):
    await asyncio.sleep(delay_seconds)
    task_db[task_id]["status"] = "QUEUED"
    await task_queue.put((task_id, prompt))
