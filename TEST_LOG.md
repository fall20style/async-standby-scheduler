# Test Log — async-standby-scheduler

- **프로젝트명**: `async-standby-scheduler`
- **최종 테스트 일시**: 2026-11-15
- **테스트 환경**: Windows 11 / PowerShell / Python 3.12.10 / pytest 9.2.0 / pytest-asyncio 1.5.0
- **최종 요약**: 전체 6개 테스트 스위트(9개 통합 테스트 케이스) **100% 통과 (`6 passed in 30.85s`)**

---

## 1. 최종 자동화 테스트 실행 결과 (`pytest -v`)

### 로그 원문
```text
(.venv) PS C:\Users\fall2\work\async_runner> .\clean_test.ps1
1. 기존 캐시 폴더(__pycache__, .pytest_cache) 및 .pyc 파일을 삭제합니다...
 - .pytest_cache 삭제 완료
 - C:\Users\fall2\work\async_runner\__pycache__ 삭제 완료

2. 가상환경(.venv) 활성화 확인...

3. 캐시 없이 pytest 자동화 테스트를 새로 시작합니다...

============================================ test session starts ============================================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\fall2\work\async_runner\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\fall2\work\async_runner
configfile: pytest.ini
plugins: asyncio-1.5.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 6 items

test_main.py::test_tc01_health_check PASSED                                                            [ 16%]
test_main.py::test_tc02_and_tc07_run_now_hello_and_nonblocking PASSED                                  [ 33%]
test_main.py::test_tc03_run_now_default_prompt PASSED                                                  [ 50%]
test_main.py::test_tc04_and_tc05_schedule_lifecycle PASSED                                             [ 66%]
test_main.py::test_tc06_worker_pool_concurrency PASSED                                                 [ 83%]
test_main.py::test_tc08_and_tc09_edge_cases PASSED                                                     [100%]

============================================ 6 passed in 30.85s =============================================
```

---

## 2. 테스트 케이스별 검증 상세 해석

| 테스트 함수 | 매핑 TC | 결과 | 검증 내용 및 동작 해석 |
| :--- | :--- | :---: | :--- |
| `test_tc01_health_check` | **TC-01** | `PASSED` | 서버 시작(`lifespan`) 시 `WORKER_POOL_SIZE = 3`만큼 워커 풀이 정상 초기화되고 `/health`가 `200 OK`를 반환함. |
| `test_tc02_and_tc07_run_now_hello_and_nonblocking` | **TC-02, TC-07** | `PASSED` | `"  HeLLo  "` 입력 시 대소문자·공백을 정규화해 `"HELLO WORLD"`를 출력했으며, 백그라운드 작업 실행 중에도 `/health` API가 블로킹 없이 즉시 응답함. |
| `test_tc03_run_now_default_prompt` | **TC-03** | `PASSED` | `"WORLD"` 등 일반 프롬프트 입력 시 기본 요약 보고서 분기가 정상 작동하여 `COMPLETED` 상태와 결과를 기록함. |
| `test_tc04_and_tc05_schedule_lifecycle` | **TC-04, TC-05** | `PASSED` | 지연 예약(2초) 등록 후 `SCHEDULED` → `RUNNING` (워커 할당) → `COMPLETED` (`HELLO WORLD`)로 상태가 정확히 전이됨. |
| `test_tc06_worker_pool_concurrency` | **TC-06** | `PASSED` | 5개 작업을 동시에 요청했을 때 최대 3개만 `RUNNING` 상태로 병렬 실행되고 나머지 2개는 `QUEUED` 상태로 대기하다가 순차 처리됨. |
| `test_tc08_and_tc09_edge_cases` | **TC-08, TC-09** | `PASSED` | 존재하지 않는 `task_id` 조회 시 예외 처리 응답을 반환하고, 필수 파라미터 누락 시 `422 Unprocessable Entity` 유효성 검사를 통과함. |

---

## 3. 테스트 중 발견된 이슈 및 트러블슈팅 기록

### 이슈 1: `pytest-asyncio` 1.5.0 픽스처 스코프 및 `anyio` 플러그인 충돌
- **현상**: 초기 `pytest` 실행 시 `PytestDeprecationWarning`과 함께 `anyio` 플러그인이 비동기 픽스처 루프를 가로채 `AssertionError` 발생.
- **해결**: `pytest.ini` 파일을 추가하여 `asyncio_mode = auto`, `asyncio_default_fixture_loop_scope = function`, `addopts = -p no:anyio` 옵션을 명시하고 `@pytest_asyncio.fixture`를 적용하여 해결.

### 이슈 2: 전역 `asyncio.Queue`의 이벤트 루프 바인딩 충돌
- **현상**: 함수 스코프(`function`)마다 새 이벤트 루프가 생성되는 테스트 환경에서, 모듈 임포트 시점에 전역으로 생성된 `task_queue = asyncio.Queue()`가 첫 번째 루프에 고정되어 후속 테스트(`TC-02`~`TC-06`)에서 이벤트 전달이 지연되는 현상 발생 (`4 failed, 2 passed`).
- **해결**: `worker_pool.py`의 `start_worker_pool()` 호출 시점마다 현재 실행 중인 이벤트 루프에 맞춰 `task_queue = asyncio.Queue()`와 `task_db.clear()`를 새로 초기화하도록 개선하여 **전체 6개 항목 모두 통과(`6 passed`)** 달성.

---

## 4. 테스트 결과 비교 요약 (Before vs After)

비동기 이벤트 루프 격리 문제 수정 전후의 `pytest` 자동화 테스트 결과 비교 요약입니다.

### ① 전체 실행 결과 비교

| 구분 | 수정 전 (`test_ncPr09.log`) | 수정 후 (`test_fix_7bS1e8.log`) | 개선 결과 |
| :--- | :---: | :---: | :--- |
| **최종 판정** | `4 failed, 2 passed` | **`6 passed`** | **통과율 33.3% → 100% 달성** |
| **총 소요 시간** | `30.86s` | `30.85s` | 모든 대기 타이머(`sleep`) 오차 없이 정상 동작 |
| **핵심 이슈** | 전역 `asyncio.Queue`의 이벤트 루프 고정 | `start_worker_pool()` 시점 큐 동적 초기화 | 함수 스코프별 독립 이벤트 루프 완벽 격리 |

### ② 테스트 케이스별 상세 비교

| 테스트 함수 | 매핑 TC | 수정 전 | 수정 후 | 원인 및 개선 상세 |
| :--- | :---: | :---: | :---: | :--- |
| `test_tc01_health_check` | **TC-01** | `PASSED` | **`PASSED`** | 서버 헬스체크 및 워커 풀 가동 상태 정상 유지 |
| `test_tc02_and_tc07_run_now_hello_and_nonblocking` | **TC-02, TC-07** | `FAILED` | **`PASSED`** | 새 이벤트 루프에 큐가 정상 바인딩되어 `"HELLO WORLD"` 즉시 처리 및 논블로킹 응답 통과 |
| `test_tc03_run_now_default_prompt` | **TC-03** | `FAILED` | **`PASSED`** | 이전 테스트의 잔여 작업 간섭 없이 일반 프롬프트 기본 분기 정상 실행 |
| `test_tc04_and_tc05_schedule_lifecycle` | **TC-04, TC-05** | `FAILED` | **`PASSED`** | 지연 예약(2초) 후 `SCHEDULED` → `RUNNING` → `COMPLETED` 상태 전이 정상 통과 |
| `test_tc06_worker_pool_concurrency` | **TC-06** | `FAILED` | **`PASSED`** | `WORKER_POOL_SIZE=3` 동시 실행 및 초과 2개 작업의 `QUEUED` 대기/순차 처리 검증 완료 |
| `test_tc08_and_tc09_edge_cases` | **TC-08, TC-09** | `PASSED` | **`PASSED`** | 예외 처리(`invalid99`) 및 파라미터 유효성 검사(`422`) 정상 유지 |
