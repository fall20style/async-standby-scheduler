\# FastAPI Async Task \& Scheduler 테스트 로그 분석



\- \*\*테스트 일시\*\*: 2026-11-15 21:53 \~ 21:54

\- \*\*테스트 환경\*\*: Windows PowerShell (`.venv` / Python 3.12 / FastAPI + Uvicorn)

\- \*\*요약\*\*: 예약 실행(`schedule`), 즉시 백그라운드 실행(`run-now`), 상태 조회(`GET`) 모두 정상 작동 확인



\---



\## 1. 서버 초기화 및 시작 로그



\### 로그 원문

```text

(.venv) PS C:\\Users\\fall2\\work\\async\_runner> python main.py

INFO:     Will watch for changes in these directories: \['C:\\\\Users\\\\fall2\\\\work\\\\async\_runner']

INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)

INFO:     Started reloader process \[33224] using StatReload

INFO:     Started server process \[8956]

INFO:     Waiting for application startup.

INFO:     Application startup complete.

```



\### 동작 해석

\- 가상환경(`.venv`)에서 `python main.py` 명령어로 Uvicorn ASGI 서버가 실행되었습니다.

\- `reload=True` 옵션에 따라 코드 변경 감지 프로세스(`33224`)와 실제 서버 프로세스(`8956`)가 분리되어 가동되었습니다.

\- FastAPI의 `lifespan` 이벤트가 정상적으로 호출되어 백그라운드 스케줄러(`AsyncIOScheduler`) 초기화가 완료(`Application startup complete`)되었습니다.



\---



\## 2. 예약 실행(Schedule) 및 조건 분기(`hello`) 테스트 로그



\### 로그 원문

```text

INFO:     127.0.0.1:52335 - "POST /tasks/schedule?prompt=hello\&delay\_seconds=5 HTTP/1.1" 200 OK

\[2026-11-15 21:53:35.170698] 작업 시작 (e6b58340): hello

\[2026-11-15 21:53:40.177707] 출력 결과 (e6b58340): HELLO WORLD

\[2026-11-15 21:53:40.177707] 작업 완료 (e6b58340)

INFO:     127.0.0.1:52343 - "GET /health HTTP/1.1" 404 Not Found

INFO:     127.0.0.1:60547 - "GET /tasks/e6b58340 HTTP/1.1" 200 OK

INFO:     127.0.0.1:49679 - "GET /health HTTP/1.1" 404 Not Found

```



\### 동작 해석

\- \*\*비동기 접수 (`200 OK`)\*\*: `prompt=hello`, `delay\_seconds=5` 요청을 받자마자 작업을 대기열에 등록하고 즉시 `200 OK` 응답을 반환했습니다.

\- \*\*지연 실행 (`21:53:35`)\*\*: 요청 시점으로부터 정확히 5초 뒤 스케줄러가 백그라운드 워커를 트리거하여 작업(`e6b58340`)을 시작했습니다.

\- \*\*조건 분기 및 완료 (`21:53:40`)\*\*: 5초간 비동기 대기(`await asyncio.sleep(5)`) 후 입력값이 `"hello"`인 조건에 따라 `"HELLO WORLD"`를 출력하고 상태를 `COMPLETED`로 변경했습니다.

\- \*\*상태 조회 (`GET /tasks/e6b58340`)\*\*: 클라이언트가 작업 ID로 결과를 조회했을 때 `200 OK`와 함께 완료된 결과를 정상 반환했습니다.

\- \*\*외부 헬스체크 (`GET /health 404`)\*\*: 로컬 PC의 외부 프로세스(IDE, 브라우저 확장 프로그램 등)가 `8000`번 포트의 서버 생존 여부를 확인하기 위해 주기적으로 `/health` 경로를 호출했으나, 해당 라우트가 아직 구현되지 않아 `404 Not Found`가 기록되었습니다.



\---



\## 3. 즉시 실행(Run-now) 및 기본 분기(`WORLD`) 테스트 로그



\### 로그 원문

```text

INFO:     127.0.0.1:60321 - "POST /tasks/run-now?prompt=WORLD HTTP/1.1" 200 OK

\[2026-11-15 21:54:13.508441] 작업 시작 (cb19ff62): WORLD

\[2026-11-15 21:54:18.515354] 출력 결과 (cb19ff62): 'WORLD'에 대한 요약 보고서 생성 완료

\[2026-11-15 21:54:18.516325] 작업 완료 (cb19ff62)

INFO:     127.0.0.1:61655 - "GET /tasks/cb19ff62 HTTP/1.1" 200 OK

INFO:     127.0.0.1:60151 - "GET /health HTTP/1.1" 404 Not Found

```



\### 동작 해석

\- \*\*즉시 백그라운드 실행 (`21:54:13`)\*\*: `BackgroundTasks`를 통해 `POST /tasks/run-now?prompt=WORLD` 요청이 들어오자마자 대기 시간 없이 백그라운드 작업(`cb19ff62`)이 시작되었습니다.

\- \*\*기본 분기 처리 (`21:54:18`)\*\*: 5초간 작업 처리 후, 입력값이 `"hello"`가 아니므로 `else` 분기가 실행되어 `'WORLD'에 대한 요약 보고서 생성 완료` 문자열을 출력하고 작업을 마쳤습니다.

\- \*\*결과 조회 및 모니터링 로그\*\*: `GET /tasks/cb19ff62`로 작업 완료 상태를 정상 확인(`200 OK`)했으며, 이후에도 외부 모니터링 도구의 `/health` 체크(`404 Not Found`)가 한 차례 더 기록되었습니다.



