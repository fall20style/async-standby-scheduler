# async-standby-scheduler

FastAPI와 Python 내장 `asyncio.Queue`를 기반으로 구현한 **24시간 상시 대기(Standby)형 비동기 작업 및 스케줄링 서버**입니다.
별도의 외부 메시지 브로커(Redis 등) 없이, API 요청 접수 계층(`main.py`)과 이벤트 기반 워커 풀 실행 계층(`worker_pool.py`)을 분리하여 논블로킹(Non-blocking)으로 작업을 처리합니다.

---

## 설치 및 실행 방법

### 1. 저장소 클론 및 폴더 이동
```powershell
git clone https://github.com<your-username>/async-standby-scheduler.git
cd async-standby-scheduler
```

### 2. 가상환경 생성 및 활성화 (Windows PowerShell 기준)
Python 3.12 환경으로 가상환경을 생성하고 활성화합니다.
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. 필수 패키지 설치
서버 실행 및 자동화 테스트(`pytest`)에 필요한 라이브러리를 설치합니다.
```powershell
pip install fastapi uvicorn pytest pytest-asyncio httpx
```

### 4. 서버 실행
```powershell
python main.py
```
서버가 시작되면 `lifespan` 핸들러를 통해 설정된 크기(`WORKER_POOL_SIZE = 3`)만큼 백그라운드 워커 풀이 자동으로 가동되며, `http://127.0.0.1:8000`에서 24시간 대기(Standby) 상태로 요청을 수신합니다.

---

## 주요 기능

- **24/7 이벤트 기반 비동기 대기 (`asyncio.Queue`)**: 주기적인 폴링(Polling) 없이 대기 상태(`await queue.get()`)를 유지하다가, 메시지가 삽입되는 즉시 워커가 깨어나 작업을 처리합니다.
- **동시성 제어 워커 풀 (`Worker Pool`)**: 고정된 개수의 워커 코루틴(`Worker-1` ~ `Worker-3`)이 작업을 나누어 처리하여 트래픽 폭주 시에도 서버 과부하를 방지합니다.
- **즉시 실행 (`POST /tasks/run-now`)**: 요청 즉시 큐에 메시지를 적재하고 `task_id`를 반환합니다.
- **지연 스케줄링 (`POST /tasks/schedule`)**: 지정된 초(`delay_seconds`) 이후에 큐로 메시지가 전달되도록 비동기 타이머를 예약합니다.
- **상태 및 담당 워커 추적 (`GET /tasks/{task_id}`)**: 작업 진행 상태(`SCHEDULED`, `QUEUED`, `RUNNING`, `COMPLETED`), 처리한 워커 이름, 최종 결과(`result`)를 조회합니다.
- **헬스체크 (`GET /health`)**: 서버 생존 상태 및 활성화된 워커 풀 크기를 반환합니다.

---

## API 수동 테스트 방법 (Swagger UI)

1. 브라우저를 열고 **`http://127.0.0`** 로 접속합니다.
2. **`POST /tasks/schedule`** 또는 **`POST /tasks/run-now`**를 선택하고 **[Try it out]**을 클릭합니다.
3. 파라미터를 입력하고 **[Execute]**를 누릅니다.
   - `prompt`: 실행할 명령어 (예: `hello` 입력 시 5초 뒤 `"HELLO WORLD"` 출력 및 저장)
   - `delay_seconds`: 예약 대기 시간(초) (예: `5`)
4. 반환된 **`task_id`**를 복사해 **`GET /tasks/{task_id}`**에서 상태 변화와 담당 워커(`worker`), 최종 결과(`result`)를 확인합니다.

---

## 자동화 테스트 실행 (`pytest`)

`main.py` 서버를 별도로 켜지 않은 상태에서 `pytest`를 통해 9개 통합 테스트 시나리오(`TC-01` ~ `TC-09`)를 한 번에 검증할 수 있습니다.

### 방법 1: 캐시 초기화 후 전체 자동 테스트 실행 (권장)
```powershell
.\clean_test.ps1
```

### 방법 2: pytest 직접 실행
```powershell
pytest -v
```

---

## 프로젝트 구조

```text
async-standby-scheduler/
├── .venv/               # Python 3.12 가상환경 폴더 (Git 제외)
├── .gitignore           # Git 추적 제외 설정 (.venv, 캐시, 로그 등)
├── main.py              # FastAPI 엔드포인트 및 서버 수명 주기(Lifespan) 관리
├── worker_pool.py       # 이벤트 기반 비동기 큐(asyncio.Queue) 및 워커 풀 모듈
├── test_main.py         # pytest 기반 통합 자동화 테스트 코드 (TC-01 ~ TC-09)
├── pytest.ini           # pytest 비동기 이벤트 루프 및 플러그인 설정
├── clean_test.ps1       # 캐시 삭제 및 자동 테스트 실행 PowerShell 스크립트
├── ARCHITECTURE.md      # 시스템 아키텍처 및 Mermaid 다이어그램 문서
├── README.md            # 프로젝트 설치, 실행 및 테스트 가이드
├── TEST_CASE.md         # 기능별 통합 테스트 케이스 명세서
└── TEST_LOG.md          # 자동화 테스트 실행 로그 및 트러블슈팅 분석
```
