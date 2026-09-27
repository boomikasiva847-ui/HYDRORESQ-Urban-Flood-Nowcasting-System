import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "module4_backend"))

from main import app
from src.database import init_db

init_db()
client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_forecast_returns_list():
    response = client.get("/forecast")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_forecast_node_returns_list():
    response = client.get("/forecast/MH_VL_014")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_history_node_returns_list():
    response = client.get("/history/MH_VL_014")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
