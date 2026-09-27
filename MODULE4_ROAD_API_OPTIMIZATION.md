# HYDRORESQ road-forecast performance fix

The real Chennai road network can contain tens of thousands of segments. The full 0-180 minute road forecast can therefore contain more than half a million records.

The application now avoids loading/serializing that entire payload for a single dashboard cycle:

- `road_forecast.json` remains the complete artifact for inspection.
- `road_forecast_cycles/road_forecast_XXX.json` stores one 5-minute cycle per file.
- `/road-forecast/summary` is a lightweight readiness check used by startup.
- `/road-forecast` returns affected roads only by default; use `include_all=true` for routing.
- Road geometry is loaded once by the dashboard and joined by `segment_id`.
- Module 6 requests the compact road forecast without geometry.

This keeps the 36-cycle forecast while avoiding the startup timeout caused by repeatedly parsing and serializing the complete road forecast.
