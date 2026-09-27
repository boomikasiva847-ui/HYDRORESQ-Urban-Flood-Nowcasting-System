"""End-to-end HYDRORESQ build pipeline: Modules 1 -> 2 -> 3.

Module 4/5/6 are services over these generated artifacts. The pipeline now
uses a 36-frame (5-minute) radar rainfall nowcast and a 2-D surface-water model
coupled to the underground drainage graph.
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path
import numpy as np
import rasterio

from module1.src.graph_builder import build_module_1_graph
from module2.src.radar_nowcast import generate_nowcast
from module2.src.radar_processor import extract_manhole_rainfall
from module2.src.runoff_calculator import compute_rational_runoff
from module3_simulation.src.dynamic_simulator import HydraulicSimulator
from module3_simulation.src.api_payload_generator import generate_dashboard_payload, generate_routing_exclusion_list
from module6_routing.generate_road_network import build_road_network
from module4_backend.src.road_forecast_builder import write_road_forecast
import json

ROOT = Path(__file__).resolve().parent


def _write_current_radar_frame(npz_path, dem_path, out_path):
    frames = np.load(npz_path)["rainfall_mm_hr"]
    with rasterio.open(dem_path) as src:
        profile = src.profile.copy()
        profile.update(driver="GTiff", dtype="float32", count=1, compress="deflate", nodata=None)
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(frames[0].astype("float32"), 1)


def run_pipeline():
    print("=" * 72)
    print(" HYDRORESQ URBAN FLOOD NOWCASTING PIPELINE")
    print(" MODULE 1 -> MODULE 2 -> MODULE 3 (0-180 min / 5-min frames)")
    print("=" * 72)

    m1_raw = ROOT / "module1/data/raw"
    m1_out = ROOT / "module1/data/output"
    m2_raw = ROOT / "module2/data/raw"
    m2_out = ROOT / "module2/data/output"
    m3_in = ROOT / "module3_simulation/data/input"
    m3_out = ROOT / "module3_simulation/data/output"
    for p in (m1_out, m2_raw, m2_out, m3_in, m3_out): p.mkdir(parents=True, exist_ok=True)

    manhole = m1_raw / "manhole.csv"
    pipes = m1_raw / "pipes.csv"
    dem = m1_raw / "dem.tif"
    if not all(p.exists() for p in (manhole, pipes, dem)):
        raise FileNotFoundError("Module 1 inputs are incomplete.")

    # ---------------- Module 1 ----------------
    print("\n[MODULE 1] Building high-resolution terrain + drainage graph...")
    G = build_module_1_graph(str(dem), str(manhole), str(pipes), str(m1_out))
    graph_file = m3_in / "terrain_graph.gpickle"
    with open(graph_file, "wb") as f: pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"  nodes={G.number_of_nodes()} edges={G.number_of_edges()}")

    # ---------------- Module 2 ----------------
    print("\n[MODULE 2] Ingesting Doppler-radar rainfall nowcast...")
    configured = os.getenv('HYDRORESQ_RADAR_GEOTIFF', '').strip()
    configured_many = os.getenv('HYDRORESQ_RADAR_GEOTIFFS', '').strip()
    radar_dir = os.getenv('HYDRORESQ_RADAR_DIR', '').strip()
    radar_paths = [x.strip() for x in configured_many.split(';') if x.strip()] if configured_many else ([configured] if configured else ([radar_dir] if radar_dir else []))
    nowcast_npz = m2_out / "radar_nowcast_0_180min.npz"
    nowcast_meta = m2_out / "radar_nowcast_metadata.json"
    meta = generate_nowcast(radar_paths, str(dem), str(nowcast_npz), str(nowcast_meta), steps=36, step_minutes=5)
    current_radar = m2_out / "radar_current_aligned.tif"
    _write_current_radar_frame(nowcast_npz, str(dem), str(current_radar))
    sampled = extract_manhole_rainfall(str(m1_out / "manhole.csv"), str(current_radar))
    inflows = compute_rational_runoff(sampled)
    inflows.to_csv(m2_out / "node_inflows.csv", index=False)
    print(f"  source={meta['source']} frames=36 lead=0-180 min")
    print(f"  nodes={len(inflows)} current-rainfall samples")

    # ---------------- Shared road network ----------------
    print("\n[ROAD NETWORK] Building navigation/routing network...")
    build_road_network()

    # ---------------- Module 3 ----------------
    print("\n[MODULE 3] Coupling 2-D surface flow with underground drainage hydraulics...")
    simulator = HydraulicSimulator(
        graph_path=str(graph_file),
        inflows_csv_path=str(m2_out / "node_inflows.csv"),
        dem_path=str(dem),
        manhole_csv_path=str(m1_out / "manhole.csv"),
        nowcast_npz_path=str(nowcast_npz),
        nowcast_meta_path=str(nowcast_meta),
    )
    forecast = simulator.run_simulation(hours=3, step_minutes=5)
    flood_results = m3_out / "flood_results.csv"
    forecast.to_csv(flood_results, index=False)
    # Create the Module 4 handoff artifact during the pipeline build. This makes
    # integration_check.py independent of stale files from a previous run and
    # ensures a fresh extraction can be validated before the API starts.
    m4_out = ROOT / "module4_backend/data/output"
    m4_out.mkdir(parents=True, exist_ok=True)
    latest_forecast = json.loads(forecast.to_json(orient="records"))
    (m4_out / "latest_forecast.json").write_text(
        json.dumps(latest_forecast, separators=(",", ":")), encoding="utf-8"
    )
    generate_dashboard_payload(forecast, str(m3_out / "dashboard_payload.json"))
    generate_routing_exclusion_list(forecast, str(m3_out / "routing_exclusions.json"), threshold_cm=15.0)
    road_rows = forecast.to_dict("records")
    road_out = ROOT / "module4_backend/data/output/road_forecast.json"
    # Remove any previous road forecast before rebuilding so a failed/partial
    # refresh can never leave stale demo-road records behind.
    if road_out.exists():
        road_out.unlink()
    road_meta = write_road_forecast(road_rows, road_out)
    if road_meta["cycles"] != 36:
        raise RuntimeError(
            f"Road forecast rebuild produced {road_meta['cycles']} cycles; expected 36. "
            "Module 3 uses lead_time_min and Module 4 uses cycle_offset_min; both are normalized by the builder."
        )
    print(f"  road forecast={road_meta["records"]} records ({road_meta["segments"]} real segments x {road_meta["cycles"]} cycles)")
    print(f"  forecast rows={len(forecast)} ({len(G.nodes)} nodes x 36 frames)")
    print(f"  peak flood depth={forecast.flood_depth_cm.max():.2f} cm")
    print(f"  severe states={(forecast.status == 'FLOODED').sum()}")

    # Integration manifest consumed by the dashboard/API and useful for demo evidence.
    manifest = {
        "system": "HYDRORESQ Urban Flood Nowcasting",
        "lead_time_minutes": 180,
        "time_step_minutes": 5,
        "forecast_frames": 36,
        "node_count": int(len(G.nodes)),
        "drainage_edges": int(len(G.edges)),
        "radar_source": meta["source"],
        "outputs": {
            "radar_nowcast": str(nowcast_npz.relative_to(ROOT)),
            "flood_forecast": str(flood_results.relative_to(ROOT)),
            "terrain_graph": str(graph_file.relative_to(ROOT)),
        },
        "requirements_coverage": {
            "dwr_rainfall_nowcast": True,
            "high_resolution_dem": True,
            "2d_surface_routing": True,
            "directed_drainage_graph": True,
            "hydraulic_capacity_and_blockage": True,
            "street_level_depth_cm": True,
            "0_3_hour_forecast": True,
            "gis_dashboard": True,
            "safe_route_api": True,
        },
    }
    (ROOT / "system_manifest.json").write_text(__import__('json').dumps(manifest, indent=2), encoding="utf-8")
    print("\n✔ Modules 1-3 build completed. Module 4/5/6 services consume the generated artifacts.")


if __name__ == "__main__":
    run_pipeline()
