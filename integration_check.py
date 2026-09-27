"""Validate the complete six-module HYDRORESQ data contracts."""
from __future__ import annotations
import csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def read_ids(path):
    with path.open(newline="", encoding="utf-8") as f:
        return {row["node_id"].strip() for row in csv.DictReader(f)}

def main():
    required = [
        ROOT / "module1/data/output/manhole.csv",
        ROOT / "module2/data/output/node_inflows.csv",
        ROOT / "module3_simulation/data/output/flood_results.csv",
        ROOT / "module4_backend/data/output/latest_forecast.json",
        ROOT / "module2/data/output/radar_nowcast_metadata.json",
        ROOT / "module4_backend/data/output/road_forecast.json",
        ROOT / "module6_routing/data/raw/road_network.geojson",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit(
            "Generated artifacts are missing. Run `python start_system.py` first (or `python run_all.py`)\n"
            + "Missing: " + "; ".join(missing)
        )

    m1 = read_ids(ROOT / "module1/data/output/manhole.csv")
    m2 = read_ids(ROOT / "module2/data/output/node_inflows.csv")
    m3_rows = list(csv.DictReader((ROOT / "module3_simulation/data/output/flood_results.csv").open(encoding="utf-8")))
    m4_data = json.loads((ROOT / "module4_backend/data/output/latest_forecast.json").read_text())
    m4 = {x["node_id"] for x in m4_data}
    road = json.loads((ROOT / "module6_routing/data/raw/road_network.geojson").read_text())
    road_features = [f for f in road.get("features", []) if f.get("geometry", {}).get("type") in {"LineString", "MultiLineString"}]
    road_nodes = {p for f in road_features for p in (f.get("properties", {}).get("u"), f.get("properties", {}).get("v")) if p}
    road_source = str(road.get("metadata", {}).get("source", "Unknown"))
    road_source_text = road_source.lower()
    radar = json.loads((ROOT / "module2/data/output/radar_nowcast_metadata.json").read_text())
    road_forecast = json.loads((ROOT / "module4_backend/data/output/road_forecast.json").read_text())
    road_segment_ids = {str(f.get("properties", {}).get("id")) for f in road_features if f.get("properties", {}).get("id")}
    forecast_segment_ids = {str(x.get("segment_id")) for x in road_forecast if x.get("segment_id")}

    print("MODULE 1 nodes:", len(m1))
    print("MODULE 2 nodes:", len(m2), "MATCH" if m1 == m2 else "MISMATCH")
    print("MODULE 3 rows:", len(m3_rows), "EXPECTED", len(m1) * 36)
    print("MODULE 4 records:", len(m4_data), "EXPECTED", len(m1) * 36)
    print("RADAR frames:", radar.get("steps"), "lead", radar.get("lead_time_minutes", [0])[0], "to", radar.get("lead_time_minutes", [0])[-1], "min")
    print("ROAD NETWORK segments:", len(road_features))
    print("ROAD NETWORK graph nodes:", len(road_nodes), "SOURCE:", road_source)
    print("ROAD forecast records:", len(road_forecast))
    print("ROAD forecast unique segments:", len(forecast_segment_ids))
    print("ROAD forecast frames:", len({int(x['cycle_offset_min']) for x in road_forecast}))

    assert m1 == m2 == m4
    assert len(m3_rows) == len(m1) * 36
    assert len(m4_data) == len(m1) * 36
    assert radar.get("steps") == 36 and radar.get("lead_time_minutes", [])[-1] == 180
    assert road_features, "No road geometries were loaded."
    assert "demo_from_drainage_alignment" not in road_source_text, "Real road network was not loaded; demo drainage connectors are not acceptable for presentation/routing."
    assert ("openstreetmap" in road_source_text or "municipal" in road_source_text or "external road" in road_source_text), (
        "A real OSM/municipal road network must be loaded before running the integration check."
    )
    assert "sample_osm_fixture" not in road_source_text, "Bundled structural road fixture is not valid for final integration."
    assert road_forecast
    assert len(forecast_segment_ids) == len(road_segment_ids), "Road forecast does not cover the current real road network."
    assert forecast_segment_ids <= road_segment_ids, "Road forecast contains IDs not present in the current road network."
    assert len({int(x['cycle_offset_min']) for x in road_forecast}) == 36
    assert all("demo_road_" not in str(x.get("segment_id", "")) for x in road_forecast), "Stale demo road forecast detected."
    required = {"surface_depth_cm", "backflow_m3s", "drain_utilization_pct", "flood_depth_cm"}
    assert required <= set(m3_rows[0])

    print("\nPASS: 0-3 hour / 5-minute nowcast contract.")
    print("PASS: 2-D surface depth + drainage surcharge contract.")
    print("PASS: real road geometry is independent of the Module 1 drainage-node IDs.")
    print("PASS: street-level road forecast is available for Module 5/6.")

if __name__ == "__main__": main()
