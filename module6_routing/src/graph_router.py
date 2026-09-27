import json
import os
import requests
import networkx as nx
try:
    from src.threshold_config import resolve_threshold
except ImportError:  # Package/test execution from project root
    from .threshold_config import resolve_threshold

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_GEOJSON = os.path.join(PROJECT_ROOT, "module6_routing", "data", "raw", "road_network.geojson")
MODULE1_MANHOLES = os.path.join(PROJECT_ROOT, "module1", "data", "output", "manhole.csv")


def _is_real_source(source: str) -> bool:
    text = str(source or '').lower()
    forbidden = ('demo_from_drainage_alignment', 'sample_osm_fixture', 'test fixture', 'fixture', 'demo fallback', 'synthetic')
    return (('openstreetmap' in text or 'municipal' in text or 'external road' in text)
            and not any(token in text for token in forbidden))


class GraphRouter:
    """Flood-aware routing graph shared with the Module 4/5 node IDs."""

    def __init__(self, geojson_path=DEFAULT_GEOJSON):
        self.geojson_path = geojson_path
        self.base_graph = nx.DiGraph()
        self.node_coordinates = {}
        self.monitoring_points = {}
        self.load_graph()

    def ensure_real_network(self):
        """Try to obtain a real OSM/municipal road network when the bundled fallback is active."""
        source = self._network_source()
        if _is_real_source(source):
            return True
        try:
            from module6_routing.generate_road_network import build_road_network
            count, new_source = build_road_network()
            if count and "demo_from_drainage_alignment" not in str(new_source).lower():
                self.base_graph = nx.DiGraph()
                self.node_coordinates = {}
                self.monitoring_points = {}
                self.load_graph()
                return True
        except Exception:
            pass
        return False

    def load_graph(self):
        if not os.path.exists(self.geojson_path):
            raise FileNotFoundError(f"Road network not found: {self.geojson_path}")

        with open(self.geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for feature in data.get("features", []):
            props = feature.get("properties", {})
            u, v = props.get("u"), props.get("v")
            weight = float(props.get("weight", 1.0) or 1.0)
            if not u or not v or u == v:
                continue

            coords = feature.get("geometry", {}).get("coordinates", [])
            attrs = {
                "weight": weight,
                "segment_id": props.get("id"),
                "name": props.get("name"),
                "source": props.get("source"),
                "geometry": coords,
            }
            self.base_graph.add_edge(u, v, **attrs)
            oneway = str(props.get("oneway", "false")).lower() in {"true", "1", "yes"}
            if not oneway:
                reverse_attrs = dict(attrs)
                reverse_attrs["geometry"] = list(reversed(coords))
                self.base_graph.add_edge(v, u, **reverse_attrs)

            if len(coords) >= 2:
                u_lon, u_lat = coords[0]
                v_lon, v_lat = coords[-1]
                self.node_coordinates.setdefault(u, {"node_id": u, "latitude": u_lat, "longitude": u_lon})
                self.node_coordinates.setdefault(v, {"node_id": v, "latitude": v_lat, "longitude": v_lon})

        # Keep Module 1 monitoring points so the UI can request routes using flood-monitoring
        # locations; endpoints are snapped to the nearest real OSM road node.
        self.monitoring_points = {}
        if os.path.exists(MODULE1_MANHOLES):
            import csv
            with open(MODULE1_MANHOLES, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    node_id = row.get("node_id")
                    point = {
                        "node_id": node_id,
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                    }
                    self.monitoring_points[node_id] = point
                    if node_id in self.base_graph:
                        self.node_coordinates[node_id] = point

    def fetch_forecast(self, cycle_offset_min=None):
        """Get the selected forecast, preferring Module 4 road data but falling back to
        a spatial projection from Module 4 node depths onto the loaded real road network.
        """
        try:
            if cycle_offset_min is None:
                resp = requests.get("http://127.0.0.1:8000/forecast", timeout=20)
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, list) or not data:
                    raise RuntimeError("Module 4 returned no flood forecast records")
                offsets = [float(x.get("cycle_offset_min", 0)) for x in data if x.get("cycle_offset_min") is not None]
                cycle_offset_min = max(offsets) if offsets else None

            road_url = "http://127.0.0.1:8000/road-forecast"
            params = {"cycle_offset_min": int(float(cycle_offset_min)), "include_all": "true"} if cycle_offset_min is not None else {"include_all": "true"}
            resp = requests.get(road_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                real = [x for x in data if "demo_from_drainage_alignment" not in str(x.get("source", "")).lower()]
                if real:
                    return real

            return self.dynamic_road_forecast(cycle_offset_min)
        except Exception as exc:
            try:
                return self.dynamic_road_forecast(cycle_offset_min)
            except Exception as dyn_exc:
                raise RuntimeError(f"Module 4 flood forecast unavailable: {exc}; dynamic road mapping failed: {dyn_exc}") from dyn_exc

    def dynamic_road_forecast(self, cycle_offset_min=None):
        """Project Module 4 monitoring-point depths onto real OSM/municipal road geometries."""
        self.ensure_real_network()
        if not _is_real_source(self._network_source()):
            raise RuntimeError("Real road geometry is not loaded. Connect to the Internet or provide HYDRORESQ_ROAD_GEOJSON.")

        resp = requests.get("http://127.0.0.1:8000/forecast", timeout=20)
        resp.raise_for_status()
        forecasts = resp.json()
        if not isinstance(forecasts, list) or not forecasts:
            raise RuntimeError("Module 4 returned no node forecast records")
        if cycle_offset_min is None:
            cycle_offset_min = max(float(x.get("cycle_offset_min", 0)) for x in forecasts)
        cycle_offset_min = int(float(cycle_offset_min))
        rows = [r for r in forecasts if int(float(r.get("cycle_offset_min", -1))) == cycle_offset_min]
        if not rows:
            raise RuntimeError(f"No node forecast exists for +{cycle_offset_min} minutes")

        from math import radians, sin, cos, sqrt, atan2
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371000.0
            dlat = radians(lat2-lat1); dlon = radians(lon2-lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
            return 2*R*atan2(sqrt(a), sqrt(max(0.0, 1.0-a)))

        roads=[]
        with open(self.geojson_path, 'r', encoding='utf-8') as f:
            geo=json.load(f)
        for feature in geo.get('features', []):
            props=feature.get('properties', {}); geom=feature.get('geometry', {})
            coords=geom.get('coordinates', [])
            if geom.get('type')!='LineString' or len(coords)<2:
                continue
            samples=[coords[0], coords[len(coords)//2], coords[-1]]
            sample_points=[(float(c[1]),float(c[0])) for c in samples if len(c)>=2]
            candidates=[]
            for row in rows:
                lat=float(row['latitude']); lon=float(row['longitude'])
                d=min(haversine(lat,lon,plat,plon) for plat,plon in sample_points)
                candidates.append((d,row))
            candidates.sort(key=lambda x:x[0])
            nearest=[r for d,r in candidates[:4] if d<=4000] or [r for _,r in candidates[:1]]
            depth=max(float(r.get('flood_depth_cm',0) or 0) for r in nearest)
            roads.append({
                'segment_id': str(props.get('id') or ''),
                'from': str(props.get('u') or ''),
                'to': str(props.get('v') or ''),
                'cycle_offset_min': cycle_offset_min,
                'flood_depth_cm': round(depth,2),
                'blocked': depth>15.0,
                'geometry': coords,
                'name': props.get('name') or props.get('ref') or props.get('id') or 'Road segment',
                'highway': props.get('highway'),
                'source': props.get('source','OpenStreetMap'),
                'mapped_forecast_node_ids':[str(r.get('node_id')) for r in nearest],
            })
        return roads

    def _snap_endpoint(self, node_id: str):
        if node_id in self.base_graph:
            return node_id
        point = self.monitoring_points.get(node_id)
        if not point:
            raise ValueError(f"Unknown origin/destination monitoring point: {node_id}")
        best = None
        best_d = float("inf")
        from math import atan2, cos, radians, sin, sqrt
        for road_node, coord in self.node_coordinates.items():
            if road_node not in self.base_graph:
                continue
            dlat = radians(float(coord["latitude"]) - point["latitude"])
            dlon = radians(float(coord["longitude"]) - point["longitude"])
            a = sin(dlat / 2) ** 2 + cos(radians(point["latitude"])) * cos(radians(float(coord["latitude"]))) * sin(dlon / 2) ** 2
            distance = 2 * 6371000.0 * atan2(sqrt(a), sqrt(max(0.0, 1.0 - a)))
            if distance < best_d:
                best_d = distance
                best = road_node
        if best is None:
            raise ValueError(f"No real road node is available near monitoring point {node_id}")
        return best

    def compute_safe_route(self, origin: str, destination: str, user_type: str, cycle_offset_min=None):
        self.ensure_real_network()
        source = self._network_source()
        if "demo_from_drainage_alignment" in str(source).lower():
            raise RuntimeError("Real road geometry is not loaded. Connect to the Internet or provide HYDRORESQ_ROAD_GEOJSON.")
        threshold = resolve_threshold(user_type)
        forecast_data = self.fetch_forecast(cycle_offset_min)
        if not forecast_data:
            raise RuntimeError("No flood forecast is available for safe routing")
        cycle_offset_min = forecast_data[0].get("cycle_offset_min", cycle_offset_min)
        segment_info = {
            str(item.get("segment_id")): {
                "depth": float(item.get("flood_depth_cm", 0.0) or 0.0),
                "coverage": str(item.get("coverage_status", "MONITORED")),
            }
            for item in forecast_data
            if item.get("segment_id") is not None
        }

        snapped_origin = self._snap_endpoint(origin)
        snapped_destination = self._snap_endpoint(destination)

        filtered_graph = self.base_graph.copy()
        avoided_segments = []

        for u, v, data in list(self.base_graph.edges(data=True)):
            segment_id = str(data.get("segment_id") or "")
            info = segment_info.get(segment_id, {"depth": 0.0, "coverage": "UNMONITORED"})
            max_depth = float(info.get("depth", 0.0) or 0.0)
            coverage = str(info.get("coverage", "UNMONITORED"))
            if max_depth > threshold:
                avoided_segments.append({
                    "edge": f"{u}-{v}",
                    "from": u,
                    "to": v,
                    "flood_depth_cm": round(max_depth, 2),
                    "reason": f"Forecast depth {max_depth:.1f} cm exceeds {user_type} threshold ({threshold:.1f} cm)"
                })
                if filtered_graph.has_edge(u, v):
                    filtered_graph.remove_edge(u, v)
            elif coverage == "UNMONITORED" and filtered_graph.has_edge(u, v):
                # Keep unmonitored roads routable but add a transparent uncertainty penalty.
                filtered_graph[u][v]["weight"] = float(filtered_graph[u][v].get("weight", 1.0)) * 1.20

        try:
            path = nx.shortest_path(filtered_graph, snapped_origin, snapped_destination, weight="weight")
            length = nx.shortest_path_length(filtered_graph, snapped_origin, snapped_destination, weight="weight")
            eta_minutes = max(1, int(round(length * 3)))
        except nx.NetworkXNoPath:
            path = []
            length = None
            eta_minutes = -1

        route_points = []
        if path:
            for idx, (u, v) in enumerate(zip(path, path[1:])):
                edge_geometry = filtered_graph.get_edge_data(u, v, {}).get("geometry") or [
                    [self.node_coordinates[u]["longitude"], self.node_coordinates[u]["latitude"]],
                    [self.node_coordinates[v]["longitude"], self.node_coordinates[v]["latitude"]],
                ]
                for point_idx, coord in enumerate(edge_geometry):
                    if not isinstance(coord, (list, tuple)) or len(coord) < 2:
                        continue
                    item = {"latitude": float(coord[1]), "longitude": float(coord[0])}
                    if route_points and point_idx == 0 and route_points[-1] == item:
                        continue
                    route_points.append(item)

        result = {
            "status": "route_found" if path else "no_safe_route",
            "user_type": user_type,
            "threshold_cm": threshold,
            "forecast_offset_min": cycle_offset_min,
            "origin": origin,
            "destination": destination,
            "snapped_origin": snapped_origin,
            "snapped_destination": snapped_destination,
            "path": path,
            "path_coordinates": route_points,
            "distance_weight": length,
            "eta_minutes": eta_minutes,
            "avoided_segments": avoided_segments,
            "forecast_nodes_used": len(forecast_data),
        }
        self.log_route(result)
        return result

    def get_network(self):
        return {
            "nodes": [self.node_coordinates[n] for n in sorted(self.base_graph.nodes())],
            "monitoring_points": list(self.monitoring_points.values()),
            "edges": [
                {
                    "from": u,
                    "to": v,
                    "weight": data.get("weight", 1.0),
                    "segment_id": data.get("segment_id"),
                    "name": data.get("name"),
                    "source": data.get("source"),
                }
                for u, v, data in self.base_graph.edges(data=True)
            ],
            "source": self._network_source(),
        }

    def _network_source(self):
        try:
            with open(self.geojson_path, "r", encoding="utf-8") as f:
                return json.load(f).get("metadata", {}).get("source", "Unknown")
        except Exception:
            return "Unknown"

    def log_route(self, route_data):
        log_path = os.path.join(PROJECT_ROOT, "module6_routing", "data", "output", "safe_routes_log.json")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        logs = []
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []
        logs.append(route_data)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)
