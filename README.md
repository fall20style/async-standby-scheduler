# Async Event-Driven Worker Pool Server (FastAPI)

FastAPI와 Python 내장 `asyncio.Queue`를 기반으로 구현한 **이벤트 기반 백그라운드 비동기 작업 및 스케줄링 서버**입니다.
별도의 외부 메시지 브로커(Redis 등) 설치 없이, API 요청 접수 계층(`main.py`)과 워커 풀 실행 계층(`worker_pool.py`)을 분리하여 논블로킹(Non-blocking)으로 작업을 처리합니다.

---

## 설치 및 실행 방법

### 1. 가상환경 생성 및 활성화 (Windows PowerShell 기준)
Python 3.12 환경으로 가상환경을 생성하고 활성화합니다.
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 필수 패키지 설치
가상환경이 활성화된 상태에서 웹 프레임워크 및 ASGI 서버만 설치합니다. (큐와 워커는 파이썬 내장 `asyncio` 사용)
```powershell
pip install fastapi uvicorn
```

### 3. 서버 실행
```powershell
python main.py
```
서버가 시작되면 `lifespan` 핸들러를 통해 설정된 크기(`WORKER_POOL_SIZE = 3`)만큼 백그라운드 워커 풀이 자동으로 가동되며, `http://127.0.0.1:8000`에서 요청을 대기합니다.

---

## 주요 기능

- **이벤트 기반 비동기 큐 (`asyncio.Queue`)**: 주기적인 폴링(Polling) 없이 메시지가 큐에 삽입되는 즉시 대기 중인 워커가 깨어나 작업을 처리합니다.
- **동시성 제어 워커 풀 (`Worker Pool`)**: 고정된 개수의 워커 코루틴(`Worker-1` ~ `Worker-3`)이 작업을 나누어 처리하여 트래픽 폭주 시에도 서버 과부하를 방지합니다.
- **즉시 실행 (`POST /tasks/run-now`)**: 요청 즉시 큐에 메시지를 적재하고 `task_id`를 반환합니다.
- **지연 스케줄링 (`POST /tasks/schedule`)**: 지정된 초(`delay_seconds`) 이후에 큐로 메시지가 전달되도록 비동기 타이머를 예약합니다.
- **상태 및 담당 워커 추적 (`GET /tasks/{task_id}`)**: 작업 진행 상태(`SCHEDULED`, `QUEUED`, `RUNNING`, `COMPLETED`), 처리한 워커 이름, 최종 결과(`result`)를 조회합니다.
- **헬스체크 (`GET /health`)**: 서버 상태 및 활성화된 워커 풀 크기를 반환합니다.

---

## API 테스트 방법 (Swagger UI)

1. 브라우저를 열고 **`http://127.0.0`** 로 접속합니다.
2. **`POST /tasks/schedule`** 또는 **`POST /tasks/run-now`**를 선택하고 **[Try it out]**을 클릭합니다.
3. 파라미터를 입력하고 **[Execute]**를 누릅니다.
   - `prompt`: 실행할 명령어 (예: `hello` 입력 시 5초 뒤 `"HELLO WORLD"` 출력 및 저장)
   - `delay_seconds`: 예약 대기 시간(초) (예: `5`)
4. 반환된 **`task_id`**를 복사해 **`GET /tasks/{task_id}`**에서 상태 변화와 담당 워커(`worker`), 최종 결과(`result`)를 확인합니다.

---

## 프로젝트 구조

```text
async_runner/
├── .venv/               # Python 3.12 가상환경 폴더
├── main.py              # FastAPI 엔드포인트 및 서버 수명 주기(Lifespan) 관리
├── worker_pool.py       # 이벤트 기반 비동기 큐(asyncio.Queue) 및 워커 풀 모듈
├── ARCHITECTURE.md      # 시스템 아키텍처 및 Mermaid 다이어그램 문서
├── README.md            # 프로젝트 설치 및 실행 가이드
└── TEST_LOG.md          # 테스트 실행 로그 분석
```
