# HYDRORESQ real-road setup

The startup process tries the Esri India Living Atlas OSM road service first, then public Overpass.
The default Chennai test area is 12.93-13.03 N, 80.18-80.27 E.

After startup, `/network` and `/road-forecast` in Module 6 can retry the real road acquisition if the first attempt failed.

For a manual retry from the project root:

```bat
python download_chennai_roads.py
python start_system.py
```

A successful setup reports `OpenStreetMap India via Esri Living Atlas` (or `OpenStreetMap via Overpass API`) and the dashboard shows `ROAD DATA: OPENSTREETMAP`.

OpenStreetMap attribution is retained on the dashboard.
