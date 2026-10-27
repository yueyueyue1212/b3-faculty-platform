@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
py -m pytest -q
pause
