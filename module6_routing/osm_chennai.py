"""Real Chennai road-network acquisition for HYDRORESQ.

Primary source: OpenStreetMap road data republished by Esri India Living Atlas
(ArcGIS Feature Service). Fallback: public Overpass API.

The output is a GeoJSON FeatureCollection containing only mapped roadway
geometries. HYDRORESQ never invents straight road links between flood/drainage
monitoring nodes.
"""
from __future__ import annotations

import json
import os
import time
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

import requests

DEFAULT_BBOX = {
    "south": float(os.getenv("HYDRORESQ_OSM_SOUTH", "12.93")),
    "west": float(os.getenv("HYDRORESQ_OSM_WEST", "80.18")),
    "north": float(os.getenv("HYDRORESQ_OSM_NORTH", "13.03")),
    "east": float(os.getenv("HYDRORESQ_OSM_EAST", "80.27")),
}

ESRI_URL = os.getenv(
    "HYDRORESQ_ESRI_ROADS_URL",
    "https://livingatlas.esri.in/server/rest/services/OSM/Roads/MapServer/0/query",
)
OVERPASS_URLS = [
    os.getenv("HYDRORESQ_OVERPASS_URL", "https://overpass-api.de/api/interpreter"),
    "https://overpass.kumi.systems/api/interpreter",
]
ROAD_CLASSES = (
    "Motorway", "Motorway Link", "Trunk", "Trunk Link", "Primary", "Primary Link",
    "Secondary", "Secondary Link", "Tertiary", "Tertiary Link", "Residential",
    "Living Street", "Unclassified", "Service",
)
HIGHWAY_REGEX = "motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified|residential|living_street|service"


def _length_m(coords: list[list[float]]) -> float:
    total = 0.0
    radius = 6371000.0
    for a, b in zip(coords, coords[1:]):
        lon1, lat1 = a
        lon2, lat2 = b
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        q = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        total += 2 * radius * atan2(sqrt(q), sqrt(max(0.0, 1.0 - q)))
    return max(total, 1.0)


def _node_id(lon: float, lat: float) -> str:
    return f"OSM_N_{lon:.7f}_{lat:.7f}"


def _esri_where() -> str:
    quoted = ",".join("'" + value.replace("'", "''") + "'" for value in ROAD_CLASSES)
    return f"fclass IN ({quoted})"


def download_chennai_roads_esri(target: str) -> dict:
    """Fetch mapped Chennai road features from the Esri-hosted OSM layer."""
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    features = []
    offset = 0
    page_size = 2000
    last_error = None

    while True:
        params = {
            "where": _esri_where(),
            "outFields": "id,fname,fclass,one_way,max_speed,district,state,country",
            "geometry": f"{DEFAULT_BBOX['west']},{DEFAULT_BBOX['south']},{DEFAULT_BBOX['east']},{DEFAULT_BBOX['north']}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outSR": "4326",
            "returnGeometry": "true",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "orderByFields": "objectid ASC",
        }
        try:
            response = requests.get(ESRI_URL, params=params, timeout=45, headers={"User-Agent": "HYDRORESQ/1.0"})
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                raise RuntimeError(str(payload["error"]))
        except Exception as exc:
            last_error = exc
            break

        page = payload.get("features", []) or []
        if not page:
            break

        for feature in page:
            attrs = feature.get("attributes") or {}
            geometry = feature.get("geometry") or {}
            paths = geometry.get("paths") or []
            for path_index, path in enumerate(paths):
                coords = [[float(x), float(y)] for x, y, *_ in path if x is not None and y is not None]
                if len(coords) < 2:
                    continue
                start = coords[0]
                end = coords[-1]
                raw_id = str(attrs.get("id") or attrs.get("objectid") or f"way_{offset}_{path_index}")
                segment_id = f"osm_{raw_id}_{path_index + 1}"
                one_way = str(attrs.get("one_way") or "").upper() in {"Y", "1", "T"}
                features.append({
                    "type": "Feature",
                    "properties": {
                        "id": segment_id,
                        "u": _node_id(start[0], start[1]),
                        "v": _node_id(end[0], end[1]),
                        "weight": round(_length_m(coords), 2),
                        "name": attrs.get("fname") or attrs.get("fclass") or "Unnamed road",
                        "highway": attrs.get("fclass"),
                        "oneway": one_way,
                        "source": "OpenStreetMap India via Esri Living Atlas",
                        "osm_way_id": raw_id,
                        "max_speed": attrs.get("max_speed"),
                        "district": attrs.get("district"),
                        "state": attrs.get("state"),
                    },
                    "geometry": {"type": "LineString", "coordinates": coords},
                })

        exceeded = bool(payload.get("exceededTransferLimit"))
        if not exceeded or len(page) < page_size:
            break
        offset += len(page)

    if not features:
        return {
            "ok": False,
            "error": str(last_error) if last_error else "No OSM road features returned by Esri service",
            "source": "unavailable",
            "bbox": DEFAULT_BBOX,
        }

    # De-duplicate exact segment IDs while keeping real geometry.
    unique = {}
    for feature in features:
        unique[(feature["properties"]["id"], tuple(map(tuple, feature["geometry"]["coordinates"])))]=feature
    features = list(unique.values())

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": "OpenStreetMap India via Esri Living Atlas",
            "provider": "Esri Living Atlas OSM Road Network",
            "bbox": DEFAULT_BBOX,
            "license_note": "Underlying OpenStreetMap data are provided under ODbL; retain OSM attribution.",
            "note": "Only actual mapped roadway geometries are included. Drainage connectors are never presented as streets.",
        },
    }
    target_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
    return {"ok": True, "features": len(features), "source": "OpenStreetMap India via Esri Living Atlas", "bbox": DEFAULT_BBOX}


def _query(bbox: dict) -> str:
    return (
        '[out:json][timeout:90];'
        f'way["highway"~"^({HIGHWAY_REGEX})$"]["access"!="private"]["area"!="yes"]'
        f'({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});'
        'out tags geom;'
    )


def download_chennai_roads_overpass(target: str) -> dict:
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    query = _query(DEFAULT_BBOX)
    last_error = None

    for url in OVERPASS_URLS:
        try:
            response = requests.post(url, data=query, timeout=120, headers={"User-Agent": "HYDRORESQ/1.0 road-loader"})
            response.raise_for_status()
            payload = response.json()
            features = []
            for element in payload.get("elements", []):
                geometry = element.get("geometry") or []
                node_ids = element.get("nodes") or []
                if len(geometry) < 2 or len(node_ids) != len(geometry):
                    continue
                tags = element.get("tags") or {}
                oneway = str(tags.get("oneway", "no")).lower() in {"yes", "1", "true"}
                name = tags.get("name") or tags.get("ref") or f"OSM road {element['id']}"
                highway = tags.get("highway")
                for idx, (a, b) in enumerate(zip(geometry, geometry[1:]), 1):
                    coords = [[float(a["lon"]), float(a["lat"])], [float(b["lon"]), float(b["lat"])]]
                    if coords[0] == coords[1]:
                        continue
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "id": f"osm_way_{element['id']}_{idx}",
                            "u": f"OSM_N_{node_ids[idx - 1]}",
                            "v": f"OSM_N_{node_ids[idx]}",
                            "weight": round(_length_m(coords), 2),
                            "name": name,
                            "highway": highway,
                            "oneway": oneway,
                            "source": "OpenStreetMap via Overpass API",
                            "osm_way_id": element["id"],
                        },
                        "geometry": {"type": "LineString", "coordinates": coords},
                    })
            if not features:
                raise RuntimeError("No drivable OSM road geometries returned")
            geojson = {
                "type": "FeatureCollection",
                "features": features,
                "metadata": {
                    "source": "OpenStreetMap via Overpass API",
                    "provider": "Overpass API",
                    "bbox": DEFAULT_BBOX,
                    "note": "Only actual mapped roadway geometries are included.",
                },
            }
            target_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
            return {"ok": True, "features": len(features), "source": "OpenStreetMap via Overpass API", "bbox": DEFAULT_BBOX}
        except Exception as exc:
            last_error = exc
            time.sleep(1)

    return {"ok": False, "error": str(last_error) if last_error else "Unknown Overpass error", "source": "unavailable", "bbox": DEFAULT_BBOX}


def download_chennai_roads(target: str) -> dict:
    """Try a robust real-data source first, then a secondary OSM API."""
    result = download_chennai_roads_esri(target)
    if result.get("ok"):
        return result
    result2 = download_chennai_roads_overpass(target)
    if result2.get("ok"):
        return result2
    return {
        "ok": False,
        "error": f"Esri OSM road service failed ({result.get('error')}); Overpass failed ({result2.get('error')})",
        "source": "unavailable",
        "bbox": DEFAULT_BBOX,
    }
