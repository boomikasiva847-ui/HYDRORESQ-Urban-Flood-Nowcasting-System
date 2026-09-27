import numpy as np
from pathlib import Path


def test_nowcast_artifact_contract():
    root = Path(__file__).resolve().parents[2]
    data = np.load(root / "module2/data/output/radar_nowcast_0_180min.npz")
    frames = data["rainfall_mm_hr"]
    assert frames.shape[0] == 36
    assert frames.ndim == 3
    assert np.isfinite(frames).all()
    assert frames.min() >= 0
