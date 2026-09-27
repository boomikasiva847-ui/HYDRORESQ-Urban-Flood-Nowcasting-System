# main.py
import sys
import os
from src.graph_builder import build_module_1_graph

def run():
    print("==================================================")
    print("      EXECUTING MODULE 1: GIS TERRAIN PROCESSING  ")
    print("==================================================")
    
    raw_manhole = "data/raw/manhole.csv"
    raw_pipes = "data/raw/pipes.csv"
    raw_dem = "data/raw/dem.tif"
    
    # Check for raw input existence
    for filepath in [raw_manhole, raw_pipes, raw_dem]:
        if not os.path.exists(filepath):
            print(f"Error: Missing input file -> {filepath}")
            print("Please ensure manhole.csv, pipes.csv, and dem.tif are placed inside data/raw/")
            sys.exit(1)
            
    try:
        graph = build_module_1_graph(
            dem_path=raw_dem,
            nodes_csv=raw_manhole,
            pipes_csv=raw_pipes,
            output_dir="data/output"
        )
        print("\nModule 1 Pipeline completed successfully!")
        print("Output artifacts ready in data/output/ for Modules 2 and 3.")
    except Exception as e:
        print(f"\nExecution Failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run()