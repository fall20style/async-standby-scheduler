import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import uvicorn
from fastapi import FastAPI, BackgroundTasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
task_db = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# 실제 백그라운드에서 돌아갈 작업 함수
async def run_agent_task(task_id: str, prompt: str):
    task_db[task_id]["status"] = "RUNNING"
    print(f"[{datetime.now()}] 작업 시작 ({task_id}): {prompt}")
    
    # 시간이 걸리는 작업 시뮬레이션 (5초 대기)
    await asyncio.sleep(5)
    
    # prompt가 'hello'일 때(대소문자 무관) "HELLO WORLD" 출력 및 저장
    if prompt.strip().lower() == "hello":
        output = "HELLO WORLD"
    else:
        output = f"'{prompt}'에 대한 요약 보고서 생성 완료"
        
    print(f"[{datetime.now()}] 출력 결과 ({task_id}): {output}")
    
    task_db[task_id]["status"] = "COMPLETED"
    task_db[task_id]["result"] = output
    print(f"[{datetime.now()}] 작업 완료 ({task_id})")

@app.post("/tasks/run-now")
async def create_immediate_task(prompt: str, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    task_db[task_id] = {"status": "PENDING", "result": None}
    
    background_tasks.add_task(run_agent_task, task_id, prompt)
    return {"message": "작업이 백그라운드에서 시작되었습니다.", "task_id": task_id}

@app.post("/tasks/schedule")
async def create_scheduled_task(prompt: str, delay_seconds: int):
    task_id = str(uuid.uuid4())[:8]
    run_time = datetime.now() + timedelta(seconds=delay_seconds)
    task_db[task_id] = {"status": f"SCHEDULED ({run_time.strftime('%H:%M:%S')})", "result": None}
    
    scheduler.add_job(
        run_agent_task,
        trigger="date",
        run_date=run_time,
        args=[task_id, prompt],
        id=task_id
    )
    return {
        "message": f"{delay_seconds}초 뒤에 실행되도록 예약되었습니다.",
        "task_id": task_id,
        "scheduled_time": run_time
    }

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    return task_db.get(task_id, {"error": "존재하지 않는 작업 ID입니다."})

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
