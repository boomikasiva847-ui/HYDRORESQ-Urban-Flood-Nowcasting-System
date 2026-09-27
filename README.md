# HYDRORESQ — Six-module Urban Flood Nowcasting System

HYDRORESQ is an end-to-end 0–3 hour urban flood nowcasting prototype for street-level flood prediction and flood-safe routing.

## Data flow

`DWR rainfall nowcast → high-resolution DEM + land-use → 2-D surface routing + drainage hydraulics → forecast API → GIS dashboard → dynamic safe routing`

### Modules

1. **GIS / Terrain / Drainage** — DEM, manholes, pipes, Manning capacity and directed drainage graph.
2. **Radar Rainfall / Runoff** — georeferenced rainfall input, 36 × 5-minute nowcast frames and Rational Method runoff.
3. **Coupled Hydraulic + 2-D Surface Model** — surface ponding, drainage capacity, surcharge/backflow and flood depth.
4. **Forecast Backend** — REST, WebSocket, SQLite history and road-segment forecast.
5. **GIS Dashboard** — 5-minute timeline, street-by-street flood depth and alerts.
6. **Dynamic Safe Routing** — flood-aware routes for commuters, transit and emergency services.

## Quick start

From the `flood_project` folder:

```bat
venv\Scripts\activate
python -m pip install -r requirements-all.txt --prefer-binary
python preflight_check.py
python start_system.py
```

Open `http://127.0.0.1:8005`.

The bundled project is a **prototype**. It uses a clearly labelled synthetic DWR-like storm only when no live radar input is configured. To use real radar rainfall:

```powershell
$env:HYDRORESQ_RADAR_GEOTIFF="C:\radar\latest_rainfall_mmhr.tif"
python start_system.py
```

See `REQUIREMENTS_COVERAGE.md` for the challenge-by-challenge mapping and production notes.

## Dependency preflight

`start_system.py` runs `preflight_check.py` before building the pipeline. If a package is missing, the startup stops with the exact install command instead of failing later inside a service.

### Real road data
The demo generates a 49-segment network from the sample drainage alignment so every forecast frame can be visualized and routed. For actual navigation, set `HYDRORESQ_ROAD_GEOJSON` to a municipal/OSM road GeoJSON with `u`, `v`, `id`, and LineString geometry.

## Windows Python 3.14 note

This package uses the Windows Selector asyncio event loop via `sitecustomize.py` and explicitly launches Uvicorn with `--loop asyncio`. This avoids the benign `WinError 10054` Proactor connection-reset traceback that can appear during localhost health checks on Windows.


## Real Chennai road data

At startup the project tries the Esri India Living Atlas OSM Road Network first, then Overpass. This avoids relying on a single Overpass endpoint. The system only renders real mapped road geometries; drainage connectors are never presented as streets. OSM attribution is retained on the map.


## FINAL ROAD-FORECAST BEHAVIOR
The startup pipeline rebuilds `module4_backend/data/output/road_forecast.json` **after** the real OSM/municipal road network is loaded and Module 3 produces the flood forecast. It also writes a fresh `latest_forecast.json` handoff so a clean extraction does not depend on stale output files. The forecast file stores flood values by real road segment ID; the Module 4 API attaches the authoritative LineString geometry from `module6_routing/data/raw/road_network.geojson` at request time. This prevents stale `demo_road_*` records from appearing over the real Chennai map.

The default configuration refuses to fall back to drainage connectors as roads. To intentionally run an offline demo-only mode, set `HYDRORESQ_ALLOW_DEMO_ROADS=1`. Do not use that mode for the final presentation.


### Road geometry safeguard
The startup pipeline treats OpenStreetMap/municipal road geometry as authoritative. Bundled sample/test fixtures are never promoted to the active dashboard road network. If the real road service is unavailable, the application fails rather than drawing drainage connectors as streets.
