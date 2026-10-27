@echo off
chcp 65001 >nul
if not exist "%~dp0frontend\dist\index.html" (
  echo [ERROR] frontend\dist\index.html not found.
  echo Run build_frontend.bat first, or start the Vite dev server instead.
  pause
  exit /b 1
)
cd /d "%~dp0backend"
echo Starting single-server demo at http://127.0.0.1:8000
echo Press Ctrl+C to stop.
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
