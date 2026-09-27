# HYDRORESQ final submission checklist

## 1. Start
Run from the extracted project root:

```bat
venv\Scripts\activate
python preflight_check.py
python start_system.py
```

Or double-click `RUN_HYDRORESQ.bat`.

## 2. Expected startup evidence

Look for:

- `All required Python packages are installed.`
- `Real OSM road geometries downloaded for Chennai test area: ...`
- `ROAD forecast frames: 36`
- all four `PASS:` integration messages
- `[READY] Module 4 Forecast API`
- `[READY] Module 6 Safe Routing API`
- `[READY] Module 5 GIS Dashboard`
- `HYDRORESQ SIX-MODULE SYSTEM IS RUNNING`

## 3. Dashboard
Open `http://127.0.0.1:8005` and press `Ctrl+F5`.

The map should use `ROAD DATA: OPENSTREETMAP`, show forecast colours on affected road geometry, list critical road segments, and allow the safe-route panel to call Module 6.

## 4. Data provenance
The bundled rainfall is a synthetic DWR-like demonstration unless a real IMD/radar GeoTIFF or radar directory is configured. The bundled road file is only a structural test fixture; the pipeline is configured to load real OSM/municipal roads before the final integration check passes.

## 5. Important final-demo requirement
Keep Internet access enabled for the first Chennai run so the real OSM road network can be downloaded, unless you already provide a real OSM/municipal GeoJSON using `HYDRORESQ_ROAD_GEOJSON`.
