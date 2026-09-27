"""Shared road-forecast builder for HYDRORESQ.

Maps the Module 3 flood-monitoring points onto the currently loaded real road
network. Road IDs/geometry come from the road GIS layer; flood depth comes
from the hydraulic forecast. Unmatched roads are marked UNMONITORED rather
than being assigned an unsupported value.
"""
from __future__ import annotations

import csv
import json
import os
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE1_MANHOLES = PROJECT_ROOT / "module1" / "data" / "output" / "manhole.csv"
ROAD_NETWORK_PATH = PROJECT_ROOT / "module6_routing" / "data" / "raw" / "road_network.geojson"

MAX_ASSOCIATION_M = float(os.getenv("HYDRORESQ_ROAD_FLOOD_RADIUS_M", "1200"))
MAX_NODES_PER_ROAD = int(os.getenv("HYDRORESQ_MAX_FLOOD_NODES_PER_ROAD", "4"))


def _cycle_offset(item: dict) -> int | None:
    """Read the canonical forecast lead time from either schema used by Modules 3/4.

    Module 3 writes `lead_time_min`; Module 4 writes `cycle_offset_min`.
    Treat both as the same 5-minute forecast-cycle coordinate.
    """
    for key in ("cycle_offset_min", "lead_time_min"):
        value = item.get(key)
        if value is None or value == "":
            continue
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            continue
    return None


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * atan2(sqrt(max(0.0, a)), sqrt(max(0.0, 1.0 - a)))


def load_monitoring_nodes() -> list[tuple[str, float, float]]:
    if not MODULE1_MANHOLES.exists():
        return []
    nodes = []
    with MODULE1_MANHOLES.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                nodes.append((str(row["node_id"]), float(row["latitude"]), float(row["longitude"])))
            except (KeyError, TypeError, ValueError):
                continue
    return nodes


def build_road_forecast(forecasts: list[dict]) -> list[dict]:
    if not ROAD_NETWORK_PATH.exists():
        return []
    try:
        geo = json.loads(ROAD_NETWORK_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    source = str(geo.get("metadata", {}).get("source", "Unknown"))
    source_text = source.lower()
    if any(token in source_text for token in ("demo_from_drainage_alignment", "fixture", "synthetic", "demo fallback")):
        return []
    feature_sources = []
    feature_ids = []
    for feature in (geo.get("features", []) or [])[:25]:
        props = feature.get("properties") or {}
        feature_sources.append(str(props.get("source", "")).lower())
        feature_ids.append(str(props.get("id", "")).lower())
    if any("fixture" in value or "demo_road_" in value for value in feature_sources + feature_ids):
        return []

    monitoring_nodes = load_monitoring_nodes()
    if not monitoring_nodes or not forecasts:
        return []

    cycles = sorted({c for x in forecasts if (c := _cycle_offset(x)) is not None})
    # Fast lookup: (cycle,node_id) -> forecast row
    forecast_by_key: dict[tuple[int, str], dict] = {}
    for item in forecasts:
        try:
            cycle = _cycle_offset(item)
            if cycle is None:
                continue
            key = (cycle, str(item.get("node_id", "")))
            forecast_by_key[key] = item
        except (TypeError, ValueError):
            continue

    # Precompute road -> nearby monitoring nodes only once.
    road_mappings: list[tuple[dict, list[str]]] = []
    for feature in geo.get("features", []):
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        if geom.get("type") != "LineString":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        samples = []
        for c in (coords[0], coords[len(coords)//2], coords[-1]):
            if isinstance(c, (list, tuple)) and len(c) >= 2:
                try:
                    samples.append((float(c[1]), float(c[0])))
                except (TypeError, ValueError):
                    pass
        if len(samples) < 2:
            continue

        candidates = []
        for node_id, lat, lon in monitoring_nodes:
            distance = min(_haversine(lat, lon, plat, plon) for plat, plon in samples)
            if distance <= MAX_ASSOCIATION_M:
                candidates.append((distance, node_id))
        candidates.sort(key=lambda x: x[0])
        mapped = [node_id for _, node_id in candidates[:MAX_NODES_PER_ROAD]]
        road_mappings.append((props, mapped))

    result: list[dict] = []
    for props, mapped_nodes in road_mappings:
        segment_id = str(props.get("id") or "")
        name = props.get("name") or props.get("ref") or props.get("fname") or segment_id or "Unnamed road"
        for cycle in cycles:
            depth_values = []
            for node_id in mapped_nodes:
                item = forecast_by_key.get((cycle, node_id))
                if item:
                    try:
                        depth_values.append(float(item.get("flood_depth_cm", 0) or 0))
                    except (TypeError, ValueError):
                        pass
            coverage = "MONITORED" if depth_values else "UNMONITORED"
            depth = max(depth_values) if depth_values else 0.0
            result.append({
                "segment_id": segment_id,
                "from": str(props.get("u") or ""),
                "to": str(props.get("v") or ""),
                "cycle_offset_min": cycle,
                "lead_time_min": cycle,
                "flood_depth_cm": round(depth, 2),
                "blocked": bool(coverage == "MONITORED" and depth > 15.0),
                "name": name,
                "highway": props.get("highway"),
                "source": props.get("source") or source,
                "coverage_status": coverage,
                "mapped_forecast_node_ids": mapped_nodes,
            })
    return result


def write_road_forecast(forecasts: list[dict], output_path: str | Path) -> dict:
    """Write the full road forecast plus one compact JSON file per forecast cycle.

    The cycle files make the HTTP API fast: a dashboard request for +60 min
    reads only that cycle instead of parsing hundreds of thousands of records.
    The full JSON remains available for inspection/backward compatibility.
    """
    rows = build_road_forecast(forecasts)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")

    cycle_dir = out.parent / "road_forecast_cycles"
    cycle_dir.mkdir(parents=True, exist_ok=True)
    for old in cycle_dir.glob("road_forecast_*.json"):
        try:
            old.unlink()
        except OSError:
            pass

    by_cycle: dict[int, list[dict]] = {}
    for row in rows:
        try:
            cycle = int(float(row.get("cycle_offset_min")))
        except (TypeError, ValueError):
            continue
        by_cycle.setdefault(cycle, []).append(row)

    summary_index = {
        "source": str(rows[0].get("source")) if rows else "Unknown",
        "cycles": {},
    }
    for cycle, cycle_rows in sorted(by_cycle.items()):
        target = cycle_dir / f"road_forecast_{cycle:03d}.json"
        target.write_text(json.dumps(cycle_rows, separators=(",", ":")), encoding="utf-8")
        depths = [float(x.get("flood_depth_cm", 0) or 0) for x in cycle_rows]
        affected = sum(1 for x in cycle_rows if float(x.get("flood_depth_cm", 0) or 0) >= 5 or bool(x.get("blocked")))
        summary_index["cycles"][str(cycle)] = {
            "status": "ok",
            "cycle_offset_min": cycle,
            "segments": len(cycle_rows),
            "affected_segments": affected,
            "max_depth_cm": round(max(depths) if depths else 0.0, 2),
        }
    (out.parent / "road_forecast_summary.json").write_text(
        json.dumps(summary_index, separators=(",", ":")), encoding="utf-8"
    )

    return {
        "records": len(rows),
        "segments": len({r.get("segment_id") for r in rows if r.get("segment_id")}),
        "cycles": len(by_cycle),
    }
