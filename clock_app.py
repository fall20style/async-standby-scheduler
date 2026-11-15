import asyncio
import json
from datetime import datetime
import httpx

SERVER_URL = "http://127.0.0.1:8000"
INTERVAL_SECONDS = 120  # 2분 = 120초


async def send_and_subscribe_time_task(client: httpx.AsyncClient):
    formatted_time = datetime.now().strftime("%Y-%m-%d-%H-%M")

    try:
        # 1. 작업 등록 요청 (POST)
        res = await client.post(
            f"{SERVER_URL}/tasks/run-now",
            params={"prompt": formatted_time},
            timeout=5.0,
        )
        res.raise_for_status()
        task_id = res.json()["task_id"]
        print(f"[Client] 1. 작업 요청 완료 -> {formatted_time} (Task ID: {task_id})")

        # 2. 폴링(반복 조회) 없이 SSE 스트림으로 완료 푸시 이벤트 수신 대기
        async with client.stream("GET", f"{SERVER_URL}/tasks/{task_id}/stream", timeout=30.0) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line.removeprefix("data: "))
                    worker_name = data.get("worker")
                    result = data.get("result")
                    print(f"[Client] 2. 서버 푸시 수신 ({worker_name}) -> {result}\n")
                    break

    except httpx.RequestError as e:
        print(f"[Client Error] 서버 연결 실패: {e}")


async def run_periodic_clock():
    print(f"=== 2분 주기 타임 스탬프 앱 시작 (SSE Push 모드 / 간격: {INTERVAL_SECONDS}초) ===")
    print("종료하려면 Ctrl + C를 누르세요.\n")

    async with httpx.AsyncClient() as client:
        while True:
            asyncio.create_task(send_and_subscribe_time_task(client))
            await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(run_periodic_clock())
    except KeyboardInterrupt:
        print("\n=== 앱이 안전하게 종료되었습니다. ===")
