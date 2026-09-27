# HYDRORESQ — final Python 3.14 startup

## Fastest way

Double-click `RUN_HYDRORESQ.bat`. It creates/uses `venv`, installs the runtime dependencies, runs the preflight check, and starts Modules 1–6.

## Manual way
```bat
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-all.txt --prefer-binary
python preflight_check.py
python start_system.py
```

Dashboard: http://127.0.0.1:8005
Forecast API: http://127.0.0.1:8000
Routing API: http://127.0.0.1:8001


For the final Chennai demo, keep internet access enabled so the real OSM road layer can be downloaded. The pipeline now rebuilds road forecasts only after the real road layer is loaded and rejects stale demo road forecasts.
