import asyncio
from datetime import datetime

task_queue: asyncio.Queue | None = None
task_db: dict = {}
task_events: dict[str, asyncio.Event] = {}  # 작업별 완료 알림 이벤트
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
                output = prompt  # 날짜 포맷 등은 입력값 그대로 깔끔하게 반환

            task_db[task_id]["status"] = "COMPLETED"
            task_db[task_id]["result"] = output
            print(f"[{datetime.now()}] [{worker_name}] 작업 완료 ({task_id}): {output}")

            # 폴링 없이 대기 중인 구독자(SSE)에게 즉시 완료 이벤트 발송
            if task_id in task_events:
                task_events[task_id].set()
        finally:
            task_queue.task_done()


def start_worker_pool(pool_size: int = WORKER_POOL_SIZE) -> list[asyncio.Task]:
    global task_queue
    task_queue = asyncio.Queue()
    task_db.clear()
    task_events.clear()
    return [
        asyncio.create_task(worker(f"Worker-{i + 1}"))
        for i in range(pool_size)
    ]


def stop_worker_pool(workers: list[asyncio.Task]):
    for w in workers:
        w.cancel()


async def enqueue_task(task_id: str, prompt: str):
    task_db[task_id] = {"status": "QUEUED", "worker": None, "result": None}
    task_events[task_id] = asyncio.Event()
    await task_queue.put((task_id, prompt))


async def enqueue_task_after_delay(delay_seconds: int, task_id: str, prompt: str):
    await asyncio.sleep(delay_seconds)
    task_db[task_id]["status"] = "QUEUED"
    await task_queue.put((task_id, prompt))
