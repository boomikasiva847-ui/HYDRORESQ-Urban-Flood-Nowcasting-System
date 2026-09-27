import csv
import json
import os
from pathlib import Path

from module6_routing.osm_chennai import download_chennai_roads

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "module6_routing/data/raw/road_network.geojson"
EXTERNAL = os.getenv("HYDRORESQ_ROAD_GEOJSON", "").strip()
MANHOLES = ROOT / "module1/data/raw/manhole.csv"
PIPES = ROOT / "module1/data/raw/pipes.csv"


def _copy_external(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection":
        raise ValueError("External road file must be a GeoJSON FeatureCollection")
    valid = []
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in {"LineString", "MultiLineString"}:
            continue
        if geometry.get("type") == "MultiLineString" and geometry.get("coordinates"):
            geometry["type"] = "LineString"
            geometry["coordinates"] = geometry["coordinates"][0]
        if len(geometry.get("coordinates", [])) < 2:
            continue
        props = feature.setdefault("properties", {})
        props.setdefault("id", f"road_{len(valid)+1:05d}")
        props.setdefault("source", "External road GeoJSON")
        coords = geometry.get("coordinates", [])
        def node_id(coord):
            return "EXT_N_" + str(round(float(coord[0]), 7)) + "_" + str(round(float(coord[1]), 7))
        props.setdefault("u", node_id(coords[0]))
        props.setdefault("v", node_id(coords[-1]))
        if "weight" not in props:
            props["weight"] = max(1.0, abs(float(coords[-1][0]) - float(coords[0][0])) * 111320.0)
        valid.append(feature)

    out = {
        "type": "FeatureCollection",
        "features": valid,
        "metadata": {
            "source": data.get("metadata", {}).get("source", "External road GeoJSON"),
            "note": "Only real road LineString geometries are rendered; drainage connector lines are not used.",
        },
    }
    TARGET.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return len(valid), out["metadata"]["source"]


def _demo_network():
    nodes = {r["node_id"]: r for r in csv.DictReader(MANHOLES.open(encoding="utf-8"))}
    features = []
    for i, row in enumerate(csv.DictReader(PIPES.open(encoding="utf-8")), 1):
        u, v = row["from_node"], row["to_node"]
        if u not in nodes or v not in nodes:
            continue
        a, b = nodes[u], nodes[v]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": f"demo_road_{i:03d}",
                    "u": u,
                    "v": v,
                    "node_ids": [u, v],
                    "weight": float(row.get("length_m", 1) or 1),
                    "source": "demo_from_drainage_alignment",
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [float(a["longitude"]), float(a["latitude"])],
                        [float(b["longitude"]), float(b["latitude"])],
                    ],
                },
            }
        )
    geo = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": "demo_from_drainage_alignment",
            "note": "Fallback only. These are not real streets and must not be rendered as roads in the dashboard.",
        },
    }
    TARGET.write_text(json.dumps(geo, indent=2), encoding="utf-8")
    return len(features), "demo_from_drainage_alignment"


def _is_real_source(source: str) -> bool:
    text = str(source or '').lower()
    forbidden = ('demo_from_drainage_alignment', 'sample_osm_fixture', 'test fixture', 'fixture', 'demo fallback', 'synthetic')
    return (('openstreetmap' in text or 'municipal' in text or 'external road' in text)
            and not any(token in text for token in forbidden))


def _network_is_real(data: dict) -> bool:
    metadata_source = data.get('metadata', {}).get('source', '')
    if not _is_real_source(metadata_source):
        return False
    features = data.get('features', []) or []
    if not features:
        return False
    # A genuine external road dataset should also have actual OSM/municipal
    # provenance at feature level. Reject bundled test fixtures even when the
    # metadata text happens to contain the words "External road".
    sample_sources = []
    sample_ids = []
    for feature in features[:25]:
        props = feature.get('properties') or {}
        sample_sources.append(str(props.get('source', '')).lower())
        sample_ids.append(str(props.get('id', '')).lower())
    forbidden = ('test fixture', 'fixture', 'sample_osm_fixture', 'demo_road_', 'demo_from_drainage_alignment')
    if any(any(token in value for token in forbidden) for value in sample_sources + sample_ids):
        return False
    return True


def _load_cached_real_network():
    if not TARGET.exists():
        return None
    try:
        data = json.loads(TARGET.read_text(encoding='utf-8'))
        if _network_is_real(data):
            return len(data.get('features', []) or []), data.get('metadata', {}).get('source', 'Unknown')
    except Exception:
        return None
    return None


def build_road_network():
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    cached = _load_cached_real_network()
    if cached and not EXTERNAL:
        n, source = cached
        print(f"[Network] Reusing cached real road network: {n} segments ({source})")
        dashboard_copy = ROOT / "module5_dashboard/data/raw/street_network.geojson"
        dashboard_copy.parent.mkdir(parents=True, exist_ok=True)
        dashboard_copy.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
        return n, source

    if EXTERNAL and Path(EXTERNAL).exists():
        n, source = _copy_external(Path(EXTERNAL))
        print(f"[Network] External real road GeoJSON used: {EXTERNAL} ({n} segments)")
    else:
        result = download_chennai_roads(str(TARGET)) if os.getenv("HYDRORESQ_AUTO_DOWNLOAD_OSM", "1") != "0" else {"ok": False, "error": "disabled"}
        if result.get("ok"):
            n, source = int(result["features"]), result.get("source", "OpenStreetMap")
            print(f"[Network] Real OSM road geometries downloaded for Chennai test area: {n} segments")
        else:
            allow_demo = os.getenv("HYDRORESQ_ALLOW_DEMO_ROADS", "0") == "1"
            if not allow_demo:
                raise RuntimeError(
                    "Real Chennai road data could not be downloaded. "
                    "HYDRORESQ refuses to use drainage connectors as roads. "
                    f"OSM source error: {result.get('error')}"
                )
            n, source = _demo_network()
            print("[Network] WARNING: DEMO road fallback explicitly enabled (HYDRORESQ_ALLOW_DEMO_ROADS=1).")
            print("[Network] ERROR:", result.get("error"))

    dashboard_copy = ROOT / "module5_dashboard/data/raw/street_network.geojson"
    dashboard_copy.parent.mkdir(parents=True, exist_ok=True)
    dashboard_copy.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
    return n, source


if __name__ == "__main__":
    build_road_network()
