# HYDRORESQ Final Verification

## Verified in this package

- Python source compilation: passed.
- JavaScript syntax checks: passed with Node.js.
- Automated unit/contract tests: 10 passed in a controlled test environment.
- Fresh `run_all.py` build followed by `integration_check.py`: passed using a controlled external-road fixture; the fresh build also created `latest_forecast.json`, fixing the clean-extraction integration failure.
- Road API summary uses a precomputed per-cycle index, so the startup readiness check does not parse the full 500k+ road forecast.
- Module 3 artifact contract: 50 nodes x 36 forecast frames.
- 0–180 minute forecast: 36 frames at 5-minute intervals.
- Real-road contract: road graph is independent of Module 1 drainage/manhole IDs.
- Road forecast cycle partitioning: one file per 5-minute cycle to avoid the previous Module 4 timeout.
- Module 4, Module 5 and Module 6 HTTP startup paths were exercised in a controlled end-to-end run.
- Module 4 `/health`, road forecast summary, Module 6 `/health`, Module 6 `/network`, and Module 5 dashboard HTML responded successfully in the controlled run.
- WebSocket initial snapshot returned 1,800 node records across 36 forecast frames.

## Windows/Python 3.14 note

The package is intended for Python 3.14. The controlled container verification used Python 3.13 because Python 3.14 is not installed in the verification container. The user's Windows environment previously verified Python 3.14.7 and successful installation of all runtime dependencies.

## Real-data requirement

For the final Chennai demonstration, keep Internet access enabled so the startup pipeline can load the real OSM road network, or set `HYDRORESQ_ROAD_GEOJSON` to an exported municipal/OSM road GeoJSON. The bundled 49-segment road file is a structural test fixture only and is not treated as a real city road dataset.

The bundled rainfall remains `SYNTHETIC_DWR_DEMO` unless `HYDRORESQ_RADAR_GEOTIFF`, `HYDRORESQ_RADAR_GEOTIFFS`, or `HYDRORESQ_RADAR_DIR` is configured. Do not present the synthetic rainfall as live Doppler-radar data.
