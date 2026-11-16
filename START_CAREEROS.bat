@echo off
cd /d "%~dp0"
if not exist .venv (
  echo Creating Python environment...
  python -m venv .venv
  if errorlevel 1 (
    echo.
    echo Python was not found. Install Python 3.12 from https://www.python.org/downloads/ then run this file again.
    echo CareerOS currently targets Python 3.12 for dependable Windows package support.
    pause
    exit /b 1
  )
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed. See errors above.& pause & exit /b 1)
echo.
echo CareerOS is starting at http://127.0.0.1:8765
timeout /t 2 >nul
start "CareerOS" http://127.0.0.1:8765
python -m backend.app
pause
