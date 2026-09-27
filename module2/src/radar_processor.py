import pandas as pd
import rasterio
from pyproj import Transformer

def extract_manhole_rainfall(manhole_csv_path, rain_grid_tif_path):
    """
    Ingests manhole coordinates and samples rainfall intensity (I in mm/hr) 
    from the GeoTIFF raster at each manhole location.
    """
    df_manholes = pd.read_csv(manhole_csv_path)

    with rasterio.open(rain_grid_tif_path) as src:
        # Prepare coordinate transformation if raster CRS differs from WGS84
        if src.crs != "EPSG:4326":
            transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            coords = [transformer.transform(lon, lat) for lon, lat in zip(df_manholes['longitude'], df_manholes['latitude'])]
        else:
            coords = list(zip(df_manholes['longitude'], df_manholes['latitude']))

        # Sample raster values at manhole locations
        intensities = [val[0] for val in src.sample(coords)]

    df_manholes['rainfall_intensity_mm_hr'] = intensities
    return df_manholes