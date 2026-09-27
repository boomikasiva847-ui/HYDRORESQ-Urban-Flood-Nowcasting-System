"""Download the real Chennai OSM road network used by HYDRORESQ.

Run from the project root:
    python download_chennai_roads.py
"""
from module6_routing.generate_road_network import build_road_network

if __name__ == "__main__":
    count, source = build_road_network()
    print(f"Road source: {source}")
    print(f"Road geometries: {count}")
    if "openstreetmap" not in str(source).lower():
        print("Real OSM data was not obtained. Check internet/Overpass access and try again.")
    else:
        print("Real OSM roads are ready for the dashboard and routing engine.")
