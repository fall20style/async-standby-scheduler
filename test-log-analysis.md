\# 테스트 결과 비교 요약 (Before vs After)



\*\*`async-standby-scheduler`\*\*의 비동기 이벤트 루프 격리 문제 수정 전후의 `pytest` 자동화 테스트 결과 비교 요약입니다.



\---



\## 1. 전체 실행 결과 요약



| 구분 | 수정 전 (`test\_ncPr09.log`) | 수정 후 (`test\_fix\_7bS1e8.log`) | 개선 결과 |

| :--- | :---: | :---: | :--- |

| \*\*최종 판정\*\* | `4 failed, 2 passed` | \*\*`6 passed`\*\* | \*\*통과율 33.3% → 100% 달성\*\* |

| \*\*총 소요 시간\*\* | `30.86s` | `30.85s` | 모든 대기 타이머(`sleep`) 오차 없이 정상 동작 |

| \*\*핵심 이슈\*\* | 전역 `asyncio.Queue`의 이벤트 루프 고정 | `start\_worker\_pool()` 시점 큐 동적 초기화 | 함수 스코프별 독립 이벤트 루프 완벽 격리 |



\---



\## 2. 테스트 케이스별 상세 비교



| 테스트 함수 | 매핑 TC | 수정 전 | 수정 후 | 원인 및 개선 상세 |

| :--- | :---: | :---: | :---: | :--- |

| `test\_tc01\_health\_check` | \*\*TC-01\*\* | `PASSED` | \*\*`PASSED`\*\* | 서버 헬스체크 및 워커 풀 가동 상태 정상 유지 |

| `test\_tc02\_and\_tc07\_run\_now\_hello\_and\_nonblocking` | \*\*TC-02, TC-07\*\* | `FAILED` | \*\*`PASSED`\*\* | 새 이벤트 루프에 큐가 정상 바인딩되어 `"HELLO WORLD"` 즉시 처리 및 논블로킹 응답 통과 |

| `test\_tc03\_run\_now\_default\_prompt` | \*\*TC-03\*\* | `FAILED` | \*\*`PASSED`\*\* | 이전 테스트의 잔여 작업 간섭 없이 일반 프롬프트 기본 분기 정상 실행 |

| `test\_tc04\_and\_tc05\_schedule\_lifecycle` | \*\*TC-04, TC-05\*\* | `FAILED` | \*\*`PASSED`\*\* | 지연 예약(2초) 후 `SCHEDULED` → `RUNNING` → `COMPLETED` 상태 전이 정상 통과 |

| `test\_tc06\_worker\_pool\_concurrency` | \*\*TC-06\*\* | `FAILED` | \*\*`PASSED`\*\* | `WORKER\_POOL\_SIZE=3` 동시 실행 및 초과 2개 작업의 `QUEUED` 대기/순차 처리 검증 완료 |

| `test\_tc08\_and\_tc09\_edge\_cases` | \*\*TC-08, TC-09\*\* | `PASSED` | \*\*`PASSED`\*\* | 예외 처리(`invalid99`) 및 파라미터 유효성 검사(`422`) 정상 유지 |



\---



\## 3. 원인 및 해결 요약



\- \*\*발생 원인\*\*: `pytest.ini`의 `asyncio\_default\_fixture\_loop\_scope = function` 설정으로 테스트마다 새 이벤트 루프가 생성되었으나, `worker\_pool.py` 전역에 미리 선언된 `task\_queue = asyncio.Queue()`가 첫 번째 루프에 바인딩된 채 유지되어 후속 테스트의 이벤트 전달이 지연됨.

\- \*\*해결 조치\*\*: `start\_worker\_pool()` 호출 시마다 현재 활성화된 이벤트 루프에서 새 `asyncio.Queue()`를 생성하고 `task\_db.clear()`를 수행하도록 수정하여 테스트 간 상태 및 루프 간섭을 원천 차단함.



