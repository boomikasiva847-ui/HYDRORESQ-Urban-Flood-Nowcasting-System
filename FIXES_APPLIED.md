# HYDRORESQ — fixes in this release

## Startup and service reliability
- Added a Module 5 `/health` endpoint in `module5_dashboard/server.py`.
- Updated `start_system.py` to use real readiness endpoints for Modules 4, 5 and 6.
- Startup now checks that ports 8000, 8001 and 8005 are available before launching services.
- Startup now reports a clear port-conflict message instead of repeatedly retrying.
- Startup now detects a service process that exits during import/startup and reports its exit code.
- Added coordinated shutdown for all child services.
- Added `preflight_check.py` so missing Python packages are reported before the pipeline starts.

## Dashboard integration
- Module 5 initial forecast loading uses Module 4 `/forecast`.
- Module 5 receives live updates through Module 4 WebSocket.
- Module 5 displays street-level road forecast from `/road-forecast`.
- Module 5 calls Module 6 `/route` and draws the returned safe route on the Leaflet map.
- Dashboard system status text now identifies the six-module system.

## Safe-routing safety fix
- Module 6 now uses Module 4's street-level `/road-forecast` data for route edge risk.
- Module 6 no longer silently treats an unavailable flood forecast as zero flood depth.
- If Module 4 is unavailable or the selected forecast cycle has no road data, `/route` returns HTTP 503 with an explanatory message.

## Validation
- 50 Module 1 nodes.
- 50 Module 2 nodes with matching IDs.
- 1,800 Module 3 flood records = 50 nodes × 36 forecast frames.
- 1,800 Module 4 forecast records.
- 36 five-minute radar-nowcast frames through +180 minutes.
- Routing road nodes use canonical `MH_VL_*` IDs.
- Integration contract checks pass.

## Recommended environment
Python 3.11 or 3.12 is recommended for broad compatibility with geospatial packages such as Rasterio, GDAL and PyProj. The project includes `requirements-all.txt` for a one-command dependency installation.
