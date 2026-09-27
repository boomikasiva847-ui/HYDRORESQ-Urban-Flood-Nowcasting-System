@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo HYDRORESQ - SIX MODULE STARTUP (PYTHON 3.14)
echo ============================================================

if not exist venv\Scripts\python.exe (
  echo [SETUP] Creating Python virtual environment...
  python -m venv venv || goto :fail
)
call venv\Scripts\activate.bat || goto :fail
python preflight_check.py >nul 2>&1
if errorlevel 1 python -m pip install -r requirements-all.txt --prefer-binary || goto :fail
python preflight_check.py || goto :fail
python start_system.py
if errorlevel 1 goto :fail

goto :done

:fail
echo.
echo HYDRORESQ failed. Read the error above.
pause
exit /b 1

:done
endlocal
