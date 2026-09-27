"""Rebuild the real-road forecast from the current Module 3 forecast.

Run from the HYDRORESQ project root after a successful pipeline build:
    python refresh_road_forecast.py
"""
from __future__ import annotations
import json
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent
FLOOD = ROOT / "module3_simulation/data/output/flood_results.csv"
OUT = ROOT / "module4_backend/data/output/road_forecast.json"


def main():
    import pandas as pd
    from module4_backend.src.road_forecast_builder import write_road_forecast
    if not FLOOD.exists():
        raise SystemExit(f"Missing flood results: {FLOOD}")
    df = pd.read_csv(FLOOD)
    if OUT.exists():
        OUT.unlink()
    stats = write_road_forecast(df.to_dict("records"), OUT)
    print(f"[ROAD FORECAST] wrote {stats['records']} records for {stats['segments']} real road segments and {stats['cycles']} forecast cycles")
    if stats["cycles"] != 36:
        raise SystemExit(f"Expected 36 forecast cycles, got {stats['cycles']}. Check Module 3 lead_time_min output.")
    if stats["records"] == 0:
        raise SystemExit("No real-road forecast records were generated. Ensure the road network is real OSM/municipal data.")

if __name__ == "__main__":
    main()
