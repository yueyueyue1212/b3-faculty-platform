@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher "py" was not found. Install Python 3.11+ first.
  pause
  exit /b 1
)
echo Starting B3 backend at http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/api/docs
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
