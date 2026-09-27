# HYDRORESQ Six-Module Integration

## End-to-end flow

`Module 1 GIS/Terrain -> Module 2 Rainfall/Runoff -> Module 3 Hydraulic Simulation -> Module 4 Forecast API -> Module 5 GIS Dashboard -> Module 6 Dynamic Safe Routing`

### Service ports

- Module 4: `http://127.0.0.1:8000`
- Module 6: `http://127.0.0.1:8001`
- Module 5: `http://127.0.0.1:8005`

## Start everything

From the `flood_project` directory:

```bash
pip install -r module4_backend/requirements.txt
pip install -r module5_dashboard/requirement.txt
pip install -r module6_routing/requirements.txt
python start_system.py
```

Then open:

`http://127.0.0.1:8005`

## What was integrated

1. **Module 4 -> Module 5 initial load**
   - Dashboard now calls `GET /forecast` when the page loads.
   - WebSocket remains enabled for later live refreshes.

2. **Module 4 -> Module 6**
   - Module 6 requests the current Module 4 forecast.
   - Routing can select `+60`, `+120`, or `+180` minute forecast cycles.
   - The router no longer mixes duplicate node records from different forecast cycles.

3. **Common node IDs**
   - Routing road endpoints now use the canonical `MH_VL_*` IDs produced by Modules 1-4.
   - The road geometry is shared by Modules 5 and 6.

4. **Module 5 -> Module 6**
   - Dashboard loads the Module 6 network.
   - User can choose origin, destination, and user type.
   - Dashboard sends `POST /route` to Module 6.
   - Returned safe route is drawn on the Leaflet map.

5. **Master pipeline**
   - `start_system.py` first executes `run_all.py` for Modules 1-3, then starts Modules 4, 6, and 5.

6. **Integration validation**
   - `python integration_check.py` validates that Modules 1-4 share the same node IDs and that Module 6 only references canonical IDs.

## Important limitation

The supplied project contains a demo/synthetic road network. The integration now makes that network consistent with the flood model, but it does **not** turn the demo road geometry into a live external road dataset. A real deployment would replace `module5_dashboard/data/raw/street_network.geojson` with a real road network and preserve the same endpoint-ID contract.

## Windows startup

Use Python 3.11 or 3.12 where possible for the geospatial dependencies. From this folder:

```bat
py -m venv venv
venv\Scripts\activate
py -m pip install --upgrade pip
pip install -r requirements-all.txt
py integration_check.py
py start_system.py
```

Open `http://127.0.0.1:8005`. Module 5 exposes `/health`, so the startup manager can verify the dashboard before declaring the six-module system ready.

If a port is already occupied, the startup manager now reports the exact port instead of repeatedly retrying. Check it with `netstat -ano | findstr :8000`, `:8001`, or `:8005`, then stop only the process you recognize.

## Dependency preflight

`start_system.py` runs `preflight_check.py` before building the pipeline. If a package is missing, the startup stops with the exact install command instead of failing later inside a service.

### Real-road integration note

The real OSM road graph has its own node IDs and is intentionally independent of Module 1's 50 hydraulic monitoring-node IDs. The integration check therefore validates that a real road source is loaded rather than incorrectly requiring road-graph node IDs to be a subset of hydraulic nodes. Road flood depths are spatially associated with nearby monitored flood points; roads outside that monitoring radius are labelled UNMONITORED rather than being assigned a misleading flood depth. Safe routing applies a small uncertainty penalty to unmonitored roads.
