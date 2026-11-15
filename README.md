\# Async Task \& Scheduler Server (FastAPI)



FastAPI와 `APScheduler`를 기반으로 구현한 \*\*백그라운드 비동기 작업 실행 및 스케줄링 서버\*\*입니다.

클라이언트의 요청을 즉시 접수해 응답을 먼저 반환한 뒤, 무거운 작업이나 예약된 작업을 백그라운드에서 논블로킹(Non-blocking) 방식으로 처리합니다.



\---



\## 설치 및 실행 방법



\### 1. 가상환경 생성 및 활성화 (Windows PowerShell 기준)

Python 3.12 환경으로 가상환경을 생성하고 활성화합니다.

```powershell

py -3.12 -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

```



\### 2. 필수 패키지 설치

가상환경이 활성화된 상태에서 필요한 라이브러리를 설치합니다.

```powershell

pip install fastapi uvicorn apscheduler

```



\### 3. 서버 실행

```powershell

python main.py

```

서버가 정상적으로 실행되면 로컬 주소(`http://127.0.0.1:8000`)에서 대기합니다.



\---



\## 주요 기능



\- \*\*즉시 백그라운드 실행 (`POST /tasks/run-now`)\*\*: FastAPI의 `BackgroundTasks`를 이용해 요청 즉시 `task\_id`를 반환하고 백그라운드에서 작업을 비동기로 수행합니다.

\- \*\*지연 스케줄링 실행 (`POST /tasks/schedule`)\*\*: `AsyncIOScheduler`를 이용해 지정된 시간(초) 이후에 작업이 자동 실행되도록 예약합니다.

\- \*\*작업 상태 추적 (`GET /tasks/{task\_id}`)\*\*: 작업의 진행 상태(`PENDING`, `SCHEDULED`, `RUNNING`, `COMPLETED`)와 실행 결과를 실시간으로 조회할 수 있습니다.

\- \*\*안전한 수명 주기 관리 (`Lifespan`)\*\*: FastAPI의 `lifespan` 컨텍스트 매니저를 적용해 서버 시작 시 스케줄러를 가동하고, 종료 시 자원을 안전하게 정리합니다.



\---



\## 기술 스택



\- \*\*Language\*\*: Python 3.12

\- \*\*Web Framework\*\*: FastAPI

\- \*\*ASGI Server\*\*: Uvicorn

\- \*\*Scheduler\*\*: APScheduler (`AsyncIOScheduler`)



\---



\## API 테스트 방법 (Swagger UI)



1\. 브라우저를 열고 \*\*`http://127.0.0`\*\* 로 접속합니다.

2\. \*\*`POST /tasks/schedule`\*\* 또는 \*\*`POST /tasks/run-now`\*\*를 선택하고 \*\*\[Try it out]\*\*을 클릭합니다.

3\. 파라미터를 입력하고 \*\*\[Execute]\*\*를 누릅니다.

&#x20;  - `prompt`: 실행할 명령어 (예: `hello` 입력 시 5초 뒤 `"HELLO WORLD"` 출력 및 저장)

&#x20;  - `delay\_seconds`: 예약 대기 시간(초) (예: `10`)

4\. 응답으로 반환된 \*\*`task\_id`\*\*를 복사해 \*\*`GET /tasks/{task\_id}`\*\*에서 상태 변화와 결과(`result`)를 확인합니다.



\---



\## 프로젝트 구조



```text

async\_runner/

├── .venv/           # Python 3.12 가상환경 폴더

├── main.py          # FastAPI 앱, 비동기 워커 및 스케줄러 로직

└── README.md        # 프로젝트 설명 및 실행 가이드

```



\---



\## 개발 시 주의사항



\- 본 서버는 Python의 `asyncio` 이벤트 루프 위에서 동작하는 비동기 서버입니다.

\- `run\_agent\_task` 내부에 실제 기능을 추가할 때는 서버 블로킹을 방지하기 위해 `time.sleep()`이나 일반 `requests` 대신 `asyncio.sleep()`, `httpx.AsyncClient` 등 비동기(`await`) 호환 라이브러리를 사용해야 합니다.



