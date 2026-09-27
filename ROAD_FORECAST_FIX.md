# Final road/flood overlay fix

## Root cause
The real OSM street layer was downloaded successfully, but the pre-existing `module4_backend/data/output/road_forecast.json` still contained cached `demo_road_*` records. Module 5 therefore rendered demo flood lines over the real OSM basemap.

## Fix
1. Build real OSM roads first.
2. Run Module 3 forecast.
3. Rebuild `road_forecast.json` from the fresh flood forecast and the current real road IDs.
4. The API attaches the current road geometry when serving `/road-forecast`.
5. Integration checks require forecast segment IDs to match the current road network and reject `demo_road_*`.
6. Default behavior refuses to use drainage connectors as road data.
