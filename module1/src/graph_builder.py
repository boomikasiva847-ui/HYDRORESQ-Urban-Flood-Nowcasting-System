# src/graph_builder.py
import os
import pickle
import pandas as pd
import networkx as nx
from .dem_processor import enrich_nodes_with_dem
from .hydraulics import calculate_pipe_capacity

def build_module_1_graph(
    dem_path: str = 'data/raw/dem.tif',
    nodes_csv: str = 'data/raw/manhole.csv',
    pipes_csv: str = 'data/raw/pipes.csv',
    output_dir: str = 'data/output'
) -> nx.DiGraph:
    """
    Constructs a directed GIS terrain network graph, embeds high-accuracy terrain
    and hydraulic capacity parameters, and exports processed artifacts.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Read input datasets
    raw_nodes = pd.read_csv(nodes_csv)
    raw_pipes = pd.read_csv(pipes_csv)
    
    # 2. Enrich node attributes using high-res DEM raster
    nodes_df = enrich_nodes_with_dem(dem_path, raw_nodes)
    
    # Save processed node mapping table (Deliverable for Module 2)
    output_csv_path = os.path.join(output_dir, 'manhole.csv')
    nodes_df.to_csv(output_csv_path, index=False)
    print(f"[Module 1] Saved enriched spatial nodes to: {output_csv_path}")
    
    # 3. Initialize NetworkX Directed Graph
    G = nx.DiGraph()
    
    # Populate Graph Nodes
    for _, row in nodes_df.iterrows():
        G.add_node(
            str(row['node_id']),
            lat=float(row['latitude']),
            lon=float(row['longitude']),
            elevation=float(row['elevation_m']),
            A_catch=float(row['catchment_area_m2']),
            A_pool=float(row['pooling_area_m2']),
            C=float(row['runoff_coefficient']),
            land_use=str(row.get('land_use', 'ROAD'))
        )
        
    # Populate Graph Edges & Compute Manning Capacities
    for _, row in raw_pipes.iterrows():
        u = str(row['from_node'])
        v = str(row['to_node'])
        length = float(row['length_m'])
        diameter = float(row['diameter_m'])
        mannings_n = float(row.get('mannings_n', 0.013))
        blockage = float(row.get('blockage_factor', 1.0))
        
        # Calculate terrain slope based on DEM node elevations
        elev_u = G.nodes[u]['elevation']
        elev_v = G.nodes[v]['elevation']
        
        # Orient flow direction downhill
        if elev_u >= elev_v:
            from_node, to_node = u, v
            slope = (elev_u - elev_v) / length
        else:
            from_node, to_node = v, u
            slope = (elev_v - elev_u) / length
            
        # Compute hydraulic discharge capacity (Q_max)
        q_max = calculate_pipe_capacity(diameter, slope, mannings_n, blockage)
        
        G.add_edge(
            from_node, to_node,
            diameter_m=diameter,
            length_m=length,
            slope=round(slope, 5),
            mannings_n=mannings_n,
            blockage_factor=blockage,
            blockage_pct=round(blockage * 100.0, 1),
            Q_max=q_max
        )
        
    # 4. Cache compiled graph (Deliverable for Module 3)
    output_pickle_path = os.path.join(output_dir, 'terrain_graph.gpickle')
    with open(output_pickle_path, 'wb') as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
        
    print(f"[Module 1] Successfully compiled terrain graph: {output_pickle_path}")
    print(f"[Module 1] Graph Summary: {len(G.nodes())} Nodes | {len(G.edges())} Pipe Edges")
    
    return G