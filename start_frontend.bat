@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"
where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found. Install Node.js 18+ first.
  pause
  exit /b 1
)
if not exist node_modules (
  echo Installing frontend dependencies...
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
)
echo Starting B3 frontend at http://127.0.0.1:5173
call npm run dev
pause
