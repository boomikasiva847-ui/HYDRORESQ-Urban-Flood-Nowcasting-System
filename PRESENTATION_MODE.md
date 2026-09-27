# HYDRORESQ Presentation Mode

This build changes the Module 5 map to a presentation-focused view:
- Safe road segments are not overdrawn; the OpenStreetMap basemap remains visible.
- Only caution/severe/blocked road segments are highlighted.
- Severe/blocked flood hotspots are shown as compact map markers.
- The forecast timeline supports all available 5-minute frames from +5 to +180 minutes.
- A critical-road list shows the highest forecast water depths for the selected time.
- Clicking a highlighted segment shows forecast time, water depth and status.

Important: the bundled road network is still marked as a demo network. For real street names and true street-by-street claims, provide a real Chennai OSM/municipal road GeoJSON via the existing project integration path.
