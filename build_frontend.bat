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
call npm run type-check
if errorlevel 1 (
  echo [ERROR] TypeScript check failed.
  pause
  exit /b 1
)
call npm run build
if errorlevel 1 (
  echo [ERROR] Frontend build failed.
  pause
  exit /b 1
)
echo Frontend built successfully: frontend\dist
pause
