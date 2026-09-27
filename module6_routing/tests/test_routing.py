from pathlib import Path
import json
from module6_routing.src.threshold_config import resolve_threshold
from module6_routing.src.graph_router import GraphRouter

ROOT = Path(__file__).resolve().parents[2]

def test_user_thresholds():
    assert resolve_threshold("commuter") == 15.0
    assert resolve_threshold("emergency") == 30.0

def test_network_has_road_graph():
    router = GraphRouter()
    assert router.base_graph.number_of_nodes() > 0
    assert router.base_graph.number_of_edges() > 0
    source = str(router._network_source()).lower()
    assert "demo_from_drainage_alignment" not in source

def test_route_computation(monkeypatch):
    router = GraphRouter()
    router.fetch_forecast = lambda cycle_offset_min=None: [
        {"node_id": "MH_VL_016", "flood_depth_cm": 0.0},
        {"node_id": "MH_VL_030", "flood_depth_cm": 0.0},
    ]
    result = router.compute_safe_route("MH_VL_016", "MH_VL_030", "commuter", 60)
    assert "path" in result
    assert "avoided_segments" in result
    assert result["user_type"] == "commuter"
    assert result["status"] in {"route_found", "no_safe_route"}
