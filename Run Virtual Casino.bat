@echo off
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  python run.py
) else (
  py -3 run.py
)
pause
