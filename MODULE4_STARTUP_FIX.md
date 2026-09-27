# Module 4 startup fix

The startup timeout was caused by Module 4 rebuilding the full real-road forecast (15,641 segments x 36 cycles = 563,076 JSON records) a second time inside the FastAPI startup event. The end-to-end pipeline already creates `module4_backend/data/output/road_forecast.json` before Module 4 starts.

The fixed scheduler reuses the prebuilt real-road forecast when it exists, and only rebuilds it if the artifact is missing. The startup health-check window is also extended to 90 seconds with a 5-second per-request timeout.
