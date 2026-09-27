"""Standalone Module 2 rainfall-nowcast + runoff runner."""
from pathlib import Path
import os
import numpy as np
import rasterio
from src.radar_nowcast import generate_nowcast
from src.radar_processor import extract_manhole_rainfall
from src.runoff_calculator import compute_rational_runoff

ROOT = Path(__file__).resolve().parent

def main():
    raw = ROOT / "data/raw"; out = ROOT / "data/output"; out.mkdir(parents=True, exist_ok=True)
    dem = ROOT.parent / "module1/data/raw/dem.tif"
    manholes = ROOT.parent / "module1/data/output/manhole.csv"
    radar = os.getenv("HYDRORESQ_RADAR_GEOTIFF", "")
    npz = out / "radar_nowcast_0_180min.npz"
    meta = out / "radar_nowcast_metadata.json"
    generate_nowcast([radar] if radar else [], str(dem), str(npz), str(meta), 36, 5)
    frames = np.load(npz)["rainfall_mm_hr"]
    with rasterio.open(dem) as src:
        profile = src.profile.copy(); profile.update(driver="GTiff", dtype="float32", count=1, nodata=None)
        current = out / "radar_current_aligned.tif"
        with rasterio.open(current, "w", **profile) as dst: dst.write(frames[0].astype("float32"), 1)
    sampled = extract_manhole_rainfall(str(manhole), str(current))
    df = compute_rational_runoff(sampled)
    df.to_csv(out / "node_inflows.csv", index=False)
    print(f"Module 2 complete: {len(frames)} rainfall frames, {len(df)} nodes")

if __name__ == "__main__": main()
