@echo off
setlocal
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  echo [SETUP] Creating Python 3.14 virtual environment...
  python -m venv venv || exit /b 1
)
call venv\Scripts\activate.bat
python preflight_check.py >nul 2>&1
if errorlevel 1 python -m pip install -r requirements-all.txt --prefer-binary || exit /b 1
python preflight_check.py || exit /b 1
python start_system.py
endlocal
