@echo off
cd /d "%~dp0\.."
if not exist .venv\Scripts\python.exe exit /b 1
.venv\Scripts\python.exe -c "import asyncio, json; from backend.app import init_db, discover, briefing; init_db(); result=asyncio.run(discover()); print(json.dumps({'discovery':result,'briefing':briefing()},ensure_ascii=False,indent=2))" >> data\daily_run.log 2>&1
