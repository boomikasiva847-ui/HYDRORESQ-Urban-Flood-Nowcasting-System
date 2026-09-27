# tests/test_graph.py
import pickle
from pathlib import Path
import pandas as pd
import networkx as nx

ROOT = Path(__file__).resolve().parents[2]

def test_module_1_artifacts():
    print("--- Running Verification Tests for Module 1 Outputs ---")

    csv_path = ROOT / "module1/data/output/manhole.csv"
    pickle_path = ROOT / "module1/data/output/terrain_graph.gpickle"

    df = pd.read_csv(csv_path)
    assert not df.empty, "Test Failed: output manhole.csv is empty."
    required_cols = ['node_id', 'latitude', 'longitude', 'elevation_m', 'catchment_area_m2', 'pooling_area_m2', 'runoff_coefficient']
    for col in required_cols:
        assert col in df.columns, f"Test Failed: Missing required column '{col}' in manhole.csv"

    with open(pickle_path, "rb") as f:
        G = pickle.load(f)

    assert isinstance(G, nx.DiGraph), "Test Failed: Loaded object is not a NetworkX DiGraph."
    assert len(G.nodes()) > 0, "Test Failed: Graph contains no nodes."
    assert len(G.edges()) > 0, "Test Failed: Graph contains no edges."

    sample_node_attrs = G.nodes[list(G.nodes())[0]]
    for attr in ['lat', 'lon', 'elevation', 'A_catch', 'A_pool', 'C']:
        assert attr in sample_node_attrs, f"Test Failed: Missing attribute '{attr}' on node."

    sample_edge_attrs = G.edges[list(G.edges())[0]]
    for attr in ['diameter_m', 'length_m', 'slope', 'Q_max']:
        assert attr in sample_edge_attrs, f"Test Failed: Missing attribute '{attr}' on edge."

    print(f"Passed: Module 1 artifacts verified ({len(G.nodes())} nodes, {len(G.edges())} edges).")
