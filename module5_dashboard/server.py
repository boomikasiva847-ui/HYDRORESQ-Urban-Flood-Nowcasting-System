import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Module 5 Command Dashboard Server")

# Get path to root module5_dashboard directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

# Mount static web assets and raw GeoJSON file endpoints
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/data/raw", StaticFiles(directory=RAW_DATA_DIR), name="raw_data")


@app.get("/")
async def serve_dashboard():
    """Serve the single-page Leaflet command dashboard."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
async def health_check():
    """Readiness endpoint used by start_system.py."""
    return {
        "status": "ok",
        "service": "module5-dashboard",
        "dashboard": "/",
        "module4_forecast": "http://127.0.0.1:8000",
        "module6_routing": "http://127.0.0.1:8001",
    }
