# HYDRORESQ — Requirement audit and implementation status

| Requirement | Current implementation | Status |
|---|---|---|
| DWR rainfall nowcast | Module 2 accepts one GeoTIFF, a directory, or multiple GeoTIFF frames; 36 × 5-minute aligned frames are produced. Synthetic storm is explicitly labelled when no radar is supplied. | **Implemented / demo input** |
| High-resolution DEM | GeoTIFF DEM is reprojected/aligned and used cell-by-cell by the 2-D surface model. | **Implemented** |
| Micro-topography + imperviousness | DEM drives D8 flow; manhole land-use/runoff coefficients drive rainfall-to-runoff. A true land-use raster can be added later. | **Prototype** |
| Directed underground drainage graph | Manholes are nodes and pipes are directed edges. Edge capacity uses Manning + blockage loss. | **Implemented** |
| Hydraulic capacity | Full-pipe Manning capacity with blockage fraction. `0.25` means 25% capacity loss. | **Implemented** |
| Blockage / overcapacity / backflow | Network solver routes node runoff through downstream pipe capacities; capacity shortfalls become surcharge/backflow and overflow volume. | **Implemented** |
| 2-D surface routing | 8-neighbour D8 surface routing runs at every 5-minute rainfall frame and couples drainage removal at inlet cells. | **Prototype 2-D** |
| 0–3 hour forecast | 36 frames at 5-minute intervals, +5 through +180 minutes. | **Implemented** |
| Street-level depth | Flood depth is reported at manholes/intersections and projected onto every mapped road segment. | **Implemented for mapped network** |
| Dynamic Web GIS | Leaflet dashboard reads Module 4 REST + WebSocket, timeline controls every forecast frame, and colours road segments by depth. | **Implemented** |
| Flood-safe navigation API | Module 6 removes segments exceeding the requested threshold for commuter/transit/emergency profiles and returns route, avoided segments and ETA. | **Implemented** |
| Navigation-map interface | Supports an external road GeoJSON via `HYDRORESQ_ROAD_GEOJSON`; OSRM client hook is included for navigation geometry. Demo fallback generates 49 aligned segments from the sample network. | **Interface implemented / demo network** |

## Important demo-vs-production distinction

The ZIP is runnable offline. Therefore its bundled rainfall and road layers are **demonstration data**, not a live municipal Doppler-radar feed or an authoritative city road database. For a real deployment, provide a current georeferenced radar rainfall product and a municipal/OSM road network. The core interfaces remain unchanged.

### Live radar

Use one current radar raster:
```powershell
$env:HYDRORESQ_RADAR_GEOTIFF="C:\radar\latest_rainfall_mmhr.tif"
```
Or a directory / sequence of radar frames:
```powershell
$env:HYDRORESQ_RADAR_DIR="C:\radar\frames"
```

### Real road network

Provide a GeoJSON whose features contain `u`, `v`, `id` and LineString coordinates. Then:
```powershell
$env:HYDRORESQ_ROAD_GEOJSON="C:\data\city_roads.geojson"
```
The `u` and `v` node IDs should correspond to forecast nodes, or an ingestion adapter should map road endpoints to the nearest forecast node.

## Model limitation

The surface component is a fast D8 nowcasting approximation, not a full Saint-Venant shallow-water solver. It is appropriate for a transparent prototype and demo; operational use should replace Module 3 with a calibrated 2-D hydrodynamic solver while retaining the same forecast contract.


### Real road geometry safeguard
The presentation map and routing engine prefer real OSM or municipal road LineString geometry. Synthetic drainage-alignment connectors are hidden from the dashboard and safe routing is disabled when no real road source is available.
