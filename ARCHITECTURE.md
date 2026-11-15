# System Architecture (Event-Driven Worker Pool)

본 문서는 외부 인프라(Redis 등) 없이 Python `asyncio` 이벤트 루프 위에서 **API 서버(`main.py`)**와 **비동기 워커 풀(`worker_pool.py`)**을 분리한 아키텍처 구조와 동작 흐름을 정의합니다.

---

## 1. 아키텍처 개요

### 핵심 설계 원칙
- **제로 폴링 & 이벤트 드리븐 (Zero-Polling & Event-Driven)**: 워커가 반복 조회(`sleep`)로 자원을 낭비하지 않고 `await task_queue.get()`에서 대기하다가, 메시지 삽입(`put`) 이벤트가 발생하는 즉시 깨어나 작업을 수행합니다.
- **워커 풀 기반 동시성 제어 (Bounded Concurrency)**: `WORKER_POOL_SIZE`만큼 미리 생성된 워커 코루틴이 작업을 순차적으로 소비하므로, 동시 요청이 폭주해도 시스템 리소스와 외부 API 호출량을 안전하게 통제할 수 있습니다.
- **모듈 간 관심사 분리 (Separation of Concerns)**: HTTP 라우팅(`main.py`)과 큐/워커 생명주기 관리(`worker_pool.py`)를 별도 모듈로 분리해, 향후 분산 메시지 브로커(Redis, RabbitMQ)로의 확장이 용이합니다.

---

## 2. 아키텍처 다이어그램

### ① 컴포넌트 구성도 (Component Architecture)

```mermaid
flowchart LR
    Client["Client<br/>(Web / Mobile / Swagger)"]
    API["FastAPI Server<br/>(main.py)"]
    Timer["Async Delay Timer<br/>(enqueue_task_after_delay)"]
    Queue[["Event-Driven Queue<br/>(asyncio.Queue)"]]
    Store[("In-Memory Store<br/>(task_db)")]
    
    subgraph Pool ["Worker Pool (worker_pool.py)"]
        W1["Worker-1"]
        W2["Worker-2"]
        W3["Worker-3"]
    end

    Client -- "1. 즉시/예약 요청" --> API
    API -- "2a. 즉시 적재 (put)" --> Queue
    API -- "2b. 지연 예약 등록" --> Timer
    Timer -- "지연 경과 후 적재 (put)" --> Queue
    API -. "3. 즉시 응답 (task_id)" .-> Client
    
    Queue -- "4. 이벤트 수신 (await get)" --> W1 & W2 & W3
    W1 & W2 & W3 -- "5. 상태 및 결과 갱신" --> Store
    Client -- "6. 상태/결과 조회 (GET)" --> API
    API -- "7. 데이터 조회" --> Store
```

### ② 이벤트 기반 작업 처리 흐름 (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor User as Client
    participant API as FastAPI (main.py)
    participant Queue as asyncio.Queue
    participant Worker as Worker Pool (Worker-1~3)
    participant DB as task_db (State Store)

    Note over API, Worker: 서버 시작(lifespan) 시 Worker-1~3 생성 및 await queue.get() 대기

    User->>API: POST /tasks/run-now (prompt="hello")
    API->>DB: 상태 초기화 (status="QUEUED")
    API->>Queue: await task_queue.put((task_id, "hello"))
    API-->>User: 200 OK (task_id 즉시 반환)

    Queue-->>Worker: 큐 삽입 이벤트 발생 (대기 중인 워커 즉시 깨어남)
    activate Worker
    Worker->>DB: 상태 업데이트 (status="RUNNING", worker="Worker-1")
    Note right of Worker: 비동기 작업 수행 (5초 대기 후 "HELLO WORLD" 생성)
    Worker->>DB: 완료 기록 (status="COMPLETED", result="HELLO WORLD")
    Worker->>Queue: task_queue.task_done()
    deactivate Worker

    User->>API: GET /tasks/{task_id}
    API->>DB: 작업 상태 및 결과 조회
    DB-->>API: status="COMPLETED", worker="Worker-1", result="HELLO WORLD"
    API-->>User: 200 OK (최종 결과 반환)
```

---

## 3. 모듈별 상세 역할

| 모듈 / 컴포넌트 | 파일 | 주요 역할 |
| :--- | :--- | :--- |
| **API Gateway / Producer** | `main.py` | - `/tasks/run-now`, `/tasks/schedule`, `/tasks/{task_id}`, `/health` 엔드포인트 제공<br>- 서버 시작/종료 시 `lifespan`을 통해 워커 풀 시작(`start_worker_pool`) 및 종료(`stop_worker_pool`) 제어 |
| **Queue & Worker Pool** | `worker_pool.py` | - `asyncio.Queue` 기반 이벤트 드리븐 메시지 큐 운영<br>- 지정된 수(`WORKER_POOL_SIZE`)의 워커 코루틴 생성 및 비동기 작업 실행<br>- 지연 실행 타이머(`enqueue_task_after_delay`) 및 상태 저장소(`task_db`) 관리 |

---

## 4. 기술 스택 (Tech Stack)

- **Language**: `Python 3.12`
- **Web Framework**: `FastAPI` (비동기 ASGI 웹 프레임워크)
- **ASGI Server**: `Uvicorn`
- **Concurrency & Queue**: `Python asyncio` (`asyncio.Queue`, `asyncio.Task`)
