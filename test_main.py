import asyncio
import json
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app, lifespan


@pytest_asyncio.fixture
async def client():
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# TC-01: 서버 헬스체크 및 워커 풀 가동 확인
async def test_tc01_health_check(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "active_workers": 3}


# TC-02 & TC-07: 즉시 실행("hello" 조건 분기) 및 논블로킹 응답성 검증
async def test_tc02_and_tc07_run_now_hello_and_nonblocking(client):
    res = await client.post("/tasks/run-now", params={"prompt": "  HeLLo  "})
    assert res.status_code == 200
    task_id = res.json()["task_id"]

    # TC-07: 백그라운드 작업이 도는 도중에도 /health가 블로킹 없이 즉시 응답하는지 확인
    health_res = await client.get("/health")
    assert health_res.status_code == 200

    await asyncio.sleep(5.5)

    data = (await client.get(f"/tasks/{task_id}")).json()
    assert data["status"] == "COMPLETED"
    assert data["result"] == "HELLO WORLD"
    assert data["worker"] in ["Worker-1", "Worker-2", "Worker-3"]


# TC-03: 일반 프롬프트(타임스탬프 등) 원본 출력 반환 검증
async def test_tc03_run_now_default_prompt(client):
    sample_timestamp = "2026-11-15-23-46"
    res = await client.post("/tasks/run-now", params={"prompt": sample_timestamp})
    task_id = res.json()["task_id"]

    await asyncio.sleep(5.5)

    data = (await client.get(f"/tasks/{task_id}")).json()
    assert data["status"] == "COMPLETED"
    assert data["result"] == sample_timestamp


# TC-04 & TC-05: 지연 스케줄링 및 단계별 상태 전이(SCHEDULED -> RUNNING -> COMPLETED)
async def test_tc04_and_tc05_schedule_lifecycle(client):
    res = await client.post("/tasks/schedule", params={"prompt": "hello", "delay_seconds": 2})
    assert res.status_code == 200
    task_id = res.json()["task_id"]

    # 1단계: 예약 직후 (SCHEDULED 상태 확인)
    data_scheduled = (await client.get(f"/tasks/{task_id}")).json()
    assert data_scheduled["status"].startswith("SCHEDULED")
    assert data_scheduled["worker"] is None

    # 2단계: 2초 지연 후 작업 실행 중 (RUNNING 상태 확인)
    await asyncio.sleep(2.5)
    data_running = (await client.get(f"/tasks/{task_id}")).json()
    assert data_running["status"] == "RUNNING"
    assert data_running["worker"] is not None

    # 3단계: 5초 처리 완료 후 (COMPLETED 상태 확인)
    await asyncio.sleep(5.0)
    data_completed = (await client.get(f"/tasks/{task_id}")).json()
    assert data_completed["status"] == "COMPLETED"
    assert data_completed["result"] == "HELLO WORLD"


# TC-06: 워커 풀 동시성 제어 (WORKER_POOL_SIZE=3 초과 요청 시 큐 대기 검증)
async def test_tc06_worker_pool_concurrency(client):
    task_ids = []
    for i in range(5):
        res = await client.post("/tasks/run-now", params={"prompt": f"task_{i}"})
        task_ids.append(res.json()["task_id"])

    await asyncio.sleep(0.5)

    statuses = [(await client.get(f"/tasks/{tid}")).json()["status"] for tid in task_ids]
    assert statuses.count("RUNNING") == 3
    assert statuses.count("QUEUED") == 2

    await asyncio.sleep(10.5)

    final_statuses = [(await client.get(f"/tasks/{tid}")).json()["status"] for tid in task_ids]
    assert all(s == "COMPLETED" for s in final_statuses)


# TC-08 & TC-09: 예외 및 유효성 검증
async def test_tc08_and_tc09_edge_cases(client):
    res_not_found = await client.get("/tasks/invalid99")
    assert res_not_found.status_code == 200
    assert res_not_found.json() == {"error": "존재하지 않는 작업 ID입니다."}

    res_invalid_param = await client.post("/tasks/schedule", params={"prompt": "hello"})
    assert res_invalid_param.status_code == 422


# TC-10: SSE 스트림(/tasks/{task_id}/stream) 무폴링 푸시 수신 검증
async def test_tc10_sse_stream_push(client):
    res = await client.post("/tasks/run-now", params={"prompt": "2026-11-15-23-50"})
    task_id = res.json()["task_id"]

    received_payload = None
    # 반복 GET 조회 없이 SSE 스트림 연결을 열어두고 푸시 데이터 수신
    async with client.stream("GET", f"/tasks/{task_id}/stream") as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                received_payload = json.loads(line.removeprefix("data: "))
                break

    assert received_payload is not None
    assert received_payload["status"] == "COMPLETED"
    assert received_payload["result"] == "2026-11-15-23-50"
    assert received_payload["worker"] in ["Worker-1", "Worker-2", "Worker-3"]

    # 존재하지 않는 task_id로 스트림 요청 시 예외 응답 검증
    invalid_stream = await client.get("/tasks/unknown_id/stream")
    assert invalid_stream.json() == {"error": "존재하지 않는 작업 ID입니다."}
