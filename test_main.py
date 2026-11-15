import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from main import app, lifespan


# FastAPI의 lifespan(워커 풀 시작/종료)을 테스트마다 자동 실행하는 픽스처
@pytest.fixture
async def client():
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# TC-01: 서버 헬스체크 및 워커 풀 가동 확인
@pytest.mark.asyncio
async def test_tc01_health_check(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "active_workers": 3}


# TC-02 & TC-07: 즉시 실행("hello" 조건 분기) 및 논블로킹 응답성 검증
@pytest.mark.asyncio
async def test_tc02_and_tc07_run_now_hello_and_nonblocking(client):
    res = await client.post("/tasks/run-now", params={"prompt": "  HeLLo  "})
    assert res.status_code == 200
    task_id = res.json()["task_id"]

    # TC-07: 백그라운드 작업이 도는 도중에도 /health가 블로킹 없이 즉시 응답하는지 확인
    health_res = await client.get("/health")
    assert health_res.status_code == 200

    # 작업 완료 대기 (5초 작업 + 여유 0.5초)
    await asyncio.sleep(5.5)

    status_res = await client.get(f"/tasks/{task_id}")
    data = status_res.json()
    assert data["status"] == "COMPLETED"
    assert data["result"] == "HELLO WORLD"
    assert data["worker"] in ["Worker-1", "Worker-2", "Worker-3"]


# TC-03: 일반 프롬프트 기본 분기 검증
@pytest.mark.asyncio
async def test_tc03_run_now_default_prompt(client):
    res = await client.post("/tasks/run-now", params={"prompt": "WORLD"})
    task_id = res.json()["task_id"]

    await asyncio.sleep(5.5)

    data = (await client.get(f"/tasks/{task_id}")).json()
    assert data["status"] == "COMPLETED"
    assert data["result"] == "'WORLD'에 대한 요약 보고서 생성 완료"


# TC-04 & TC-05: 지연 스케줄링 및 단계별 상태 전이(SCHEDULED -> RUNNING -> COMPLETED)
@pytest.mark.asyncio
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
@pytest.mark.asyncio
async def test_tc06_worker_pool_concurrency(client):
    task_ids = []
    # 5개 작업 연속 등록
    for i in range(5):
        res = await client.post("/tasks/run-now", params={"prompt": f"task_{i}"})
        task_ids.append(res.json()["task_id"])

    await asyncio.sleep(0.5)

    # 3개만 RUNNING이고, 나머지 2개는 QUEUED 대기 상태여야 함
    statuses = [(await client.get(f"/tasks/{tid}")).json()["status"] for tid in task_ids]
    assert statuses.count("RUNNING") == 3
    assert statuses.count("QUEUED") == 2

    # 모든 작업이 순차 완료될 때까지 대기 (1라운드 5초 + 2라운드 5초 + 여유 0.5초)
    await asyncio.sleep(10.5)

    final_statuses = [(await client.get(f"/tasks/{tid}")).json()["status"] for tid in task_ids]
    assert all(s == "COMPLETED" for s in final_statuses)


# TC-08 & TC-09: 예외 및 유효성 검증
@pytest.mark.asyncio
async def test_tc08_and_tc09_edge_cases(client):
    # TC-08: 존재하지 않는 task_id
    res_not_found = await client.get("/tasks/invalid99")
    assert res_not_found.status_code == 200
    assert res_not_found.json() == {"error": "존재하지 않는 작업 ID입니다."}

    # TC-09: 필수 파라미터(delay_seconds) 누락
    res_invalid_param = await client.post("/tasks/schedule", params={"prompt": "hello"})
    assert res_invalid_param.status_code == 422
