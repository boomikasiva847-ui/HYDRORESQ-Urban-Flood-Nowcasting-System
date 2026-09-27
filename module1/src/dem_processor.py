# src/dem_processor.py
import rasterio
import numpy as np
import pandas as pd
from pyproj import Transformer

def enrich_nodes_with_dem(dem_path: str, nodes_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts high-resolution elevation from dem.tif at exact node coordinates
    and derives street-level catchment and pooling properties.
    """
    elevations = []
    
    with rasterio.open(dem_path) as src:
        # Check DEM CRS and build transformer if coordinates are WGS84 (Lat/Lon)
        dem_crs = src.crs
        transformer = None
        if dem_crs and dem_crs.to_string() != "EPSG:4326":
            transformer = Transformer.from_crs("EPSG:4326", dem_crs, always_xy=True)

        for _, row in nodes_df.iterrows():
            lon, lat = float(row['longitude']), float(row['latitude'])
            
            # Reproject coordinates if DEM is in a projected CRS (e.g., UTM meters)
            if transformer:
                x_coord, y_coord = transformer.transform(lon, lat)
            else:
                x_coord, y_coord = lon, lat

            # High-accuracy spatial lookup using rasterio index
            try:
                py, px = src.index(x_coord, y_coord)
                raster_data = src.read(1)
                
                # Check bounds
                if 0 <= py < raster_data.shape[0] and 0 <= px < raster_data.shape[1]:
                    val = raster_data[py, px]
                    elevation = float(val) if val != src.nodata and not np.isnan(val) else 5.0
                else:
                    elevation = 5.0
            except IndexError:
                elevation = 5.0  # Fallback elevation if slightly out of bounding box
                
            elevations.append(round(elevation, 3))

    nodes_df['elevation_m'] = elevations
    
    # Fill or assign street-level catchment areas (A_catch) in m²
    if 'catchment_area_m2' not in nodes_df.columns:
        nodes_df['catchment_area_m2'] = 1200.0  # Standard urban inlet catchment
        
    # Fill or assign micro-pooling depression areas (A_pool) in m²
    if 'pooling_area_m2' not in nodes_df.columns:
        nodes_df['pooling_area_m2'] = 250.0    # Standard street pooling depression
        
    # Assign Runoff Coefficients (C-Factor) based on land cover
    c_map = {'ROAD': 0.9, 'CONCRETE': 0.9, 'RESIDENTIAL': 0.6, 'COMMERCIAL': 0.85, 'PARK': 0.2}
    if 'runoff_coefficient' not in nodes_df.columns:
        if 'land_use' in nodes_df.columns:
            nodes_df['runoff_coefficient'] = nodes_df['land_use'].astype(str).str.upper().map(c_map).fillna(0.9)
        else:
            nodes_df['runoff_coefficient'] = 0.9  # Default to urban impervious road surface

    return nodes_df