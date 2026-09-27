import os
import json
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import ForecastCycle
from src.websocket_manager import manager

router = APIRouter()

LATEST_FORECAST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'output', 'latest_forecast.json')
ROAD_FORECAST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'output', 'road_forecast.json')
ROAD_NETWORK_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'module6_routing', 'data', 'raw', 'road_network.geojson'))

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.get("/forecast")
def get_forecast():
    if os.path.exists(LATEST_FORECAST_PATH):
        with open(LATEST_FORECAST_PATH, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

ROAD_CYCLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'output', 'road_forecast_cycles')
ROAD_SUMMARY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'output', 'road_forecast_summary.json')

_road_geometry_cache = None
_road_source_cache = 'Unknown'

def _load_road_geometry_cache():
    """Load real road geometry once per Module 4 process."""
    global _road_geometry_cache, _road_source_cache
    if _road_geometry_cache is not None:
        return _road_geometry_cache
    cache = {}
    try:
        with open(ROAD_NETWORK_PATH, 'r', encoding='utf-8') as f:
            network = json.load(f)
        _road_source_cache = network.get('metadata', {}).get('source', 'Unknown')
        for feature in network.get('features', []):
            props = feature.get('properties') or {}
            seg = props.get('id')
            geom = feature.get('geometry') or {}
            if seg and geom.get('type') == 'LineString':
                cache[str(seg)] = {
                    'geometry': geom.get('coordinates', []),
                    'source': props.get('source') or _road_source_cache,
                    'name': props.get('name') or props.get('ref') or props.get('fname') or str(seg),
                    'highway': props.get('highway') or props.get('fclass'),
                }
    except (OSError, json.JSONDecodeError):
        cache = {}
    _road_geometry_cache = cache
    return cache

def _load_cycle_rows(cycle_offset_min: int | None):
    """Load only the selected road forecast cycle, never the 500k+ row file when possible."""
    if cycle_offset_min is None:
        cycle_offset_min = 60
    cycle = int(cycle_offset_min)
    cycle_path = os.path.join(ROAD_CYCLE_DIR, f'road_forecast_{cycle:03d}.json')
    if os.path.exists(cycle_path):
        try:
            with open(cycle_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            pass

    # Backward-compatible fallback for older generated projects.
    if not os.path.exists(ROAD_FORECAST_PATH):
        return []
    try:
        with open(ROAD_FORECAST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    return [x for x in data if int(float(x.get('cycle_offset_min', -1))) == cycle]

@router.get("/road-forecast")
def get_road_forecast(
    cycle_offset_min: int | None = None,
    include_all: bool = False,
    include_geometry: bool = False,
    min_depth_cm: float = 5.0,
):
    rows = _load_cycle_rows(cycle_offset_min)
    if not rows:
        return []

    # For the dashboard, return only roads that need attention.
    # For Module 6, include_all=true returns every road segment compactly.
    if not include_all:
        rows = [
            row for row in rows
            if float(row.get('flood_depth_cm', 0) or 0) >= float(min_depth_cm) or bool(row.get('blocked'))
        ]

    geometry = _load_road_geometry_cache() if include_geometry else {}
    out = []
    for row in rows:
        item = dict(row)
        info = geometry.get(str(row.get('segment_id')), {})
        item['source'] = row.get('source') or info.get('source') or _road_source_cache
        item['name'] = row.get('name') or info.get('name') or row.get('segment_id') or 'Road segment'
        item['highway'] = row.get('highway') or info.get('highway')
        if include_geometry:
            item['geometry'] = info.get('geometry', [])
        out.append(item)
    return out

@router.get("/road-forecast/summary")
def get_road_forecast_summary(cycle_offset_min: int | None = None):
    cycle = int(cycle_offset_min if cycle_offset_min is not None else 60)
    # Fast path: read the tiny precomputed index instead of parsing 15k road rows.
    if os.path.exists(ROAD_SUMMARY_PATH):
        try:
            with open(ROAD_SUMMARY_PATH, 'r', encoding='utf-8') as f:
                index = json.load(f)
            item = (index.get('cycles') or {}).get(str(cycle))
            if item:
                return {**item, 'source': item.get('source') or index.get('source', _road_source_cache)}
        except (OSError, json.JSONDecodeError):
            pass

    rows = _load_cycle_rows(cycle)
    if not rows:
        return {
            'status': 'empty',
            'cycle_offset_min': cycle,
            'segments': 0,
            'affected_segments': 0,
            'max_depth_cm': 0.0,
            'source': _road_source_cache,
        }
    max_depth = max(float(r.get('flood_depth_cm', 0) or 0) for r in rows)
    affected = sum(1 for r in rows if float(r.get('flood_depth_cm', 0) or 0) >= 5 or bool(r.get('blocked')))
    source = str(rows[0].get('source') or _road_source_cache)
    return {
        'status': 'ok',
        'cycle_offset_min': int(float(rows[0].get('cycle_offset_min', cycle))),
        'segments': len(rows),
        'affected_segments': affected,
        'max_depth_cm': round(max_depth, 2),
        'source': source,
    }

@router.get("/forecast/{node_id}")
def get_forecast_for_node(node_id: str):
    # Reads from the in-memory/DB snapshot and formats it as JSON on request
    # we can pull from latest_forecast.json for 36-cycle depth timeline
    if os.path.exists(LATEST_FORECAST_PATH):
        with open(LATEST_FORECAST_PATH, 'r') as f:
            try:
                data = json.load(f)
                return [d for d in data if d.get('node_id') == node_id]
            except json.JSONDecodeError:
                return []
    return []

@router.get("/history/{node_id}")
def get_history_for_node(node_id: str, db: Session = Depends(get_db)):
    records = db.query(ForecastCycle).filter(ForecastCycle.node_id == node_id).order_by(ForecastCycle.timestamp.desc()).all()
    return [
        {
            "node_id": r.node_id,
            "timestamp": r.timestamp,
            "cycle_offset_min": r.cycle_offset_min,
            "flood_depth_cm": r.flood_depth_cm,
            "blocked": r.blocked
        }
        for r in records
    ]

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send the current forecast immediately so a newly opened dashboard
        # does not have to wait five minutes for the scheduler's next broadcast.
        if os.path.exists(LATEST_FORECAST_PATH):
            try:
                with open(LATEST_FORECAST_PATH, "r", encoding="utf-8") as f:
                    snapshot = json.load(f)
                if isinstance(snapshot, list) and snapshot:
                    await websocket.send_json(snapshot)
            except Exception:
                pass
        while True:
            # Keep connection alive. Browser client sends occasional text pings.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
