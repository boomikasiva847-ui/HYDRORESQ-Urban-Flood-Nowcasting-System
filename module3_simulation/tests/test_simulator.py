import csv
from pathlib import Path


def test_end_to_end_forecast_contract():
    root = Path(__file__).resolve().parents[2]
    rows = list(csv.DictReader((root / "module3_simulation/data/output/flood_results.csv").open(encoding="utf-8")))
    assert len(rows) == 50 * 36
    assert {"lead_time_min", "surface_depth_cm", "backflow_m3s", "drain_utilization_pct", "flood_depth_cm"} <= set(rows[0])
    assert sorted({int(float(r["lead_time_min"])) for r in rows})[0] == 5
    assert sorted({int(float(r["lead_time_min"])) for r in rows})[-1] == 180
