# Integration Analysis Note — Zero-Polling SSE & Worker Pool

- **프로젝트명**: `async-standby-scheduler`
- **분석 일시**: 2026-11-15 23:49 ~ 23:57
- **실행 환경**: Windows 11 / PowerShell (`.venv` / Python 3.12) / FastAPI + Uvicorn + HTTPX
- **검증 대상**: `main.py` (API & SSE Broker) + `worker_pool.py` (Worker Pool) + `clock_app.py` (2분 주기 SSE 클라이언트)

---

## 1. 원본 실행 로그 (Raw Logs)

### ① 서버 로그 (`python main.py`)
```text
(.venv) PS C:\Users\fall2\work\async_runner> python main.py
INFO:     Will watch for changes in these directories: ['C:\\Users\\fall2\\work\\async_runner']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [35972] using StatReload
INFO:     Started server process [30512]
INFO:     Waiting for application startup.
[2026-11-15 23:49:27.498992] [Worker-1] 준비 완료 (이벤트 대기 중...)
[2026-11-15 23:49:27.498992] [Worker-2] 준비 완료 (이벤트 대기 중...)
[2026-11-15 23:49:27.498992] [Worker-3] 준비 완료 (이벤트 대기 중...)
INFO:     Application startup complete.
INFO:     127.0.0.1:60173 - "POST /tasks/run-now?prompt=2026-11-15-23-49 HTTP/1.1" 200 OK
[2026-11-15 23:49:36.823357] [Worker-1] 작업 시작 (c2bcc6c4): 2026-11-15-23-49
INFO:     127.0.0.1:60173 - "GET /tasks/c2bcc6c4/stream HTTP/1.1" 200 OK
[2026-11-15 23:49:41.840351] [Worker-1] 작업 완료 (c2bcc6c4): 2026-11-15-23-49
INFO:     127.0.0.1:64559 - "POST /tasks/run-now?prompt=2026-11-15-23-51 HTTP/1.1" 200 OK
[2026-11-15 23:51:36.503304] [Worker-2] 작업 시작 (b4616bd9): 2026-11-15-23-51
INFO:     127.0.0.1:64559 - "GET /tasks/b4616bd9/stream HTTP/1.1" 200 OK
[2026-11-15 23:51:41.524145] [Worker-2] 작업 완료 (b4616bd9): 2026-11-15-23-51
INFO:     127.0.0.1:58718 - "POST /tasks/run-now?prompt=2026-11-15-23-53 HTTP/1.1" 200 OK
[2026-11-15 23:53:36.515481] [Worker-3] 작업 시작 (5c0e3a84): 2026-11-15-23-53
INFO:     127.0.0.1:58718 - "GET /tasks/5c0e3a84/stream HTTP/1.1" 200 OK
[2026-11-15 23:53:41.512648] [Worker-3] 작업 완료 (5c0e3a84): 2026-11-15-23-53
INFO:     127.0.0.1:52661 - "POST /tasks/run-now?prompt=2026-11-15-23-55 HTTP/1.1" 200 OK
[2026-11-15 23:55:36.529477] [Worker-1] 작업 시작 (325d7fc0): 2026-11-15-23-55
INFO:     127.0.0.1:52661 - "GET /tasks/325d7fc0/stream HTTP/1.1" 200 OK
[2026-11-15 23:55:41.524963] [Worker-1] 작업 완료 (325d7fc0): 2026-11-15-23-55
INFO:     127.0.0.1:60503 - "POST /tasks/run-now?prompt=2026-11-15-23-57 HTTP/1.1" 200 OK
[2026-11-15 23:57:36.541569] [Worker-2] 작업 시작 (8bd2da53): 2026-11-15-23-57
INFO:     127.0.0.1:60503 - "GET /tasks/8bd2da53/stream HTTP/1.1" 200 OK
[2026-11-15 23:57:41.538611] [Worker-2] 작업 완료 (8bd2da53): 2026-11-15-23-57
```

### ② 클라이언트 앱 로그 (`python .\clock_app.py`)
```text
(.venv) PS C:\Users\fall2\work\async_runner> python .\clock_app.py
=== 2분 주기 타임 스탬프 앱 시작 (SSE Push 모드 / 간격: 120초) ===
종료하려면 Ctrl + C를 누르세요.

[Client] 1. 작업 요청 완료 -> 2026-11-15-23-49 (Task ID: c2bcc6c4)
[Client] 2. 서버 푸시 수신 (Worker-1) -> 2026-11-15-23-49

[Client] 1. 작업 요청 완료 -> 2026-11-15-23-51 (Task ID: b4616bd9)
[Client] 2. 서버 푸시 수신 (Worker-2) -> 2026-11-15-23-51

[Client] 1. 작업 요청 완료 -> 2026-11-15-23-53 (Task ID: 5c0e3a84)
[Client] 2. 서버 푸시 수신 (Worker-3) -> 2026-11-15-23-53

[Client] 1. 작업 요청 완료 -> 2026-11-15-23-55 (Task ID: 325d7fc0)
[Client] 2. 서버 푸시 수신 (Worker-1) -> 2026-11-15-23-55

[Client] 1. 작업 요청 완료 -> 2026-11-15-23-57 (Task ID: 8bd2da53)
[Client] 2. 서버 푸시 수신 (Worker-2) -> 2026-11-15-23-57
```

---

## 2. 통합 실행 타임라인 및 동작 요약

서버와 클라이언트 간의 8분간(총 5회 주기) 실제 통신 및 워커 할당 흐름을 하나로 결합한 요약표입니다.

| 회차 | 요청 시각 | 작업 ID | 전송 데이터 (`prompt`) | 할당 워커 | SSE 스트림 호출 | 작업 완료 시각 | 수신 결과 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **초기화** | `23:49:27` | - | 서버 `lifespan` 가동 | `Worker-1, 2, 3` | - | - | 24/7 이벤트 대기 상태 진입 |
| **1회** | `23:49:36` | `c2bcc6c4` | `2026-11-15-23-49` | **Worker-1** | **1회** (`200 OK`) | `23:49:41` (+5.01s) | `2026-11-15-23-49` |
| **2회** | `23:51:36` | `b4616bd9` | `2026-11-15-23-51` | **Worker-2** | **1회** (`200 OK`) | `23:51:41` (+5.02s) | `2026-11-15-23-51` |
| **3회** | `23:53:36` | `5c0e3a84` | `2026-11-15-23-53` | **Worker-3** | **1회** (`200 OK`) | `23:53:41` (+4.99s) | `2026-11-15-23-53` |
| **4회** | `23:55:36` | `325d7fc0` | `2026-11-15-23-55` | **Worker-1** | **1회** (`200 OK`) | `23:55:41` (+4.99s) | `2026-11-15-23-55` |
| **5회** | `23:57:36` | `8bd2da53` | `2026-11-15-23-57` | **Worker-2** | **1회** (`200 OK`) | `23:57:41` (+4.99s) | `2026-11-15-23-57` |

---

## 3. 아키텍처 핵심 검증 포인트

1. **완전한 무폴링(End-to-End Zero-Polling) 입증**
   - 서버 접근 로그를 보면 각 작업 ID당 `GET /tasks/{task_id}/stream` 요청이 **단 1회씩만** 발생했습니다.
   - 클라이언트가 완료 여부를 묻기 위해 반복 조회(`Polling`)하지 않고 SSE 스트림 연결을 열어둔 채 대기하다가, 워커의 `asyncio.Event.set()` 신호와 동시에 결과를 푸시(Push)받았음을 보여줍니다.

2. **워커 풀의 균등 라운드 로빈(Round-Robin) 분산**
   - `asyncio.Queue`에서 대기하던 3개의 워커 코루틴이 **`Worker-1` → `Worker-2` → `Worker-3` → `Worker-1` → `Worker-2`** 순서로 정확히 순환하며 작업을 균등하게 분배받았습니다.

3. **누적 지연(Time Drift) 없는 정밀한 2분 주기 실행**
   - 매 회차마다 백그라운드 작업 처리에 `5초`가 소요되었음에도, 클라이언트 앱이 비동기 태스크(`asyncio.create_task`)로 수신 대기를 분리한 덕분에 실행 시각이 **`23:49:36` → `23:51:36` → `23:53:36` → `23:55:36` → `23:57:36`**으로 오차 없이 정확히 120초 간격을 유지했습니다.

4. **HTTP Keep-Alive 커넥션 재사용**
   - 클라이언트와 서버 로그의 포트 번호(`60173`, `64559`, `58718`, `52661`, `60503`)가 `POST /tasks/run-now`와 `GET /tasks/{task_id}/stream`에서 동일하게 유지되며, `httpx.AsyncClient`의 커넥션 풀링이 효율적으로 동작하고 있음이 확인되었습니다.
	