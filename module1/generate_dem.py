"""Generate a georeferenced 10 m urban micro-topography DEM for the demo area."""
import os
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin


def create_urban_dem(output_path="data/raw/dem.tif"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    nodes = pd.read_csv("data/raw/manhole.csv")
    min_lat, max_lat = nodes.latitude.min() - 0.002, nodes.latitude.max() + 0.002
    min_lon, max_lon = nodes.longitude.min() - 0.002, nodes.longitude.max() + 0.002
    resolution = 0.00009  # about 10 m at Chennai latitude
    width = int(np.ceil((max_lon - min_lon) / resolution))
    height = int(np.ceil((max_lat - min_lat) / resolution))
    transform = from_origin(min_lon, max_lat, resolution, resolution)
    lon = min_lon + (np.arange(width) + 0.5) * resolution
    lat = max_lat - (np.arange(height) + 0.5) * resolution
    xx, yy = np.meshgrid(lon, lat)
    # Broad drainage gradient plus repeatable street-scale depressions/berms.
    xnorm = (xx - min_lon) / max(max_lon - min_lon, 1e-9)
    ynorm = (yy - min_lat) / max(max_lat - min_lat, 1e-9)
    dem = 8.0 - 3.0 * xnorm - 0.8 * ynorm
    for i, (_, r) in enumerate(nodes.iterrows()):
        sigma = 0.00035 + (i % 3) * 0.00008
        dem -= 0.22 * np.exp(-((xx-r.longitude)**2 + (yy-r.latitude)**2)/(2*sigma**2))
    rng = np.random.default_rng(42)
    dem += rng.normal(0, 0.025, dem.shape)
    metadata = {'driver':'GTiff','dtype':'float32','nodata':-9999.0,'width':width,'height':height,'count':1,'crs':'EPSG:4326','transform':transform}
    with rasterio.open(output_path, 'w', **metadata) as dst:
        dst.write(dem.astype(np.float32), 1)
    print(f"Generated georeferenced 10 m urban DEM: {output_path} ({width}x{height})")

if __name__ == '__main__':
    create_urban_dem()
