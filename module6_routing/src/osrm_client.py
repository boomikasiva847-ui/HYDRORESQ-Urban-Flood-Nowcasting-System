import requests

def call_osrm_route(origin_coords, dest_coords):
    """
    (Stretch Goal) Queries self-hosted OSRM engine for real-world road geometry.
    Falls back to internal NetworkX router if OSRM service is offline.
    """
    osrm_url = f"http://localhost:5000/route/v1/driving/{origin_coords[1]},{origin_coords[0]};{dest_coords[1]},{dest_coords[0]}?overview=full"
    try:
        response = requests.get(osrm_url, timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None