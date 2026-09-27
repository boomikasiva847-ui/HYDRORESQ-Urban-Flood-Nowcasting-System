from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
try:
    from src.graph_router import GraphRouter, _is_real_source
except ImportError:  # Package/test execution from project root
    from .graph_router import GraphRouter, _is_real_source

router = APIRouter()
graph_router = GraphRouter()


class RouteRequest(BaseModel):
    origin: str
    destination: str
    user_type: str = "commuter"
    cycle_offset_min: float | None = Field(default=None, description="Forecast cycle in minutes, e.g. 60, 120, 180")


@router.get("/health")
async def health():
    graph_router.ensure_real_network()
    source = graph_router._network_source()
    real = _is_real_source(source)
    return {
        "status": "ok",
        "service": "module6-routing",
        "nodes": graph_router.base_graph.number_of_nodes(),
        "road_source": source,
        "real_road_data": real,
    }


@router.get("/network")
async def network():
    graph_router.ensure_real_network()
    return graph_router.get_network()


@router.get("/road-forecast")
async def road_forecast(cycle_offset_min: int | None = None):
    try:
        return graph_router.dynamic_road_forecast(cycle_offset_min)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/route")
async def calculate_route(req: RouteRequest):
    try:
        return graph_router.compute_safe_route(
            origin=req.origin,
            destination=req.destination,
            user_type=req.user_type,
            cycle_offset_min=req.cycle_offset_min,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
