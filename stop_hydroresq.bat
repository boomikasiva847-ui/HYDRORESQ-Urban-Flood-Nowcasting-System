@echo off
echo Stopping HYDRORESQ Python services...
taskkill /F /IM python.exe >nul 2>&1
echo Done.
