"""Preflight dependency check for the HYDRORESQ six-module demo."""
from __future__ import annotations
import importlib.util
import sys

REQUIRED = {
    "numpy": "numpy",
    "pandas": "pandas",
    "rasterio": "rasterio",
    "pyproj": "pyproj",
    "networkx": "networkx",
    "shapely": "shapely",
    "requests": "requests",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "apscheduler": "apscheduler",
    "sqlalchemy": "sqlalchemy",
    "websockets": "websockets",
    "jinja2": "jinja2",
    "pydantic": "pydantic",
}


def main() -> None:
    print("[PREFLIGHT] Python:", sys.version.split()[0])
    missing = [name for name, module in REQUIRED.items() if importlib.util.find_spec(module) is None]
    if missing:
        print("[PREFLIGHT] Missing packages:")
        for name in missing:
            print("  -", name)
        print("[PREFLIGHT] Install all dependencies with:")
        print("  python -m pip install --upgrade pip")
        print("  python -m pip install -r requirements-all.txt --prefer-binary")
        raise SystemExit(1)
    print("[PREFLIGHT] All required Python packages are installed.")


if __name__ == "__main__":
    main()
