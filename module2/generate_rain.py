import os
import numpy as np
import rasterio
from rasterio.transform import from_origin

def generate_synthetic_rain_grid(output_path="data/raw/rain_grid.tif"):
    """Generates a synthetic cloudburst rainfall raster (80 to 120 mm/hr) over Velachery."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Grid dimensions (100x100 pixels around Velachery, Chennai ~ 12.97-12.99 N, 80.21-80.23 E)
    width, height = 100, 100
    west, north = 80.21, 12.99
    pixel_size = 0.0002
    
    transform = from_origin(west, north, pixel_size, pixel_size)
    
    # Create cloudburst rain intensities between 80 mm/hr and 120 mm/hr
    x, y = np.meshgrid(np.linspace(-2, 2, width), np.linspace(-2, 2, height))
    gaussian_peak = np.exp(-(x**2 + y**2))
    rain_grid = (80.0 + gaussian_peak * 40.0).astype(np.float32)

    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=rain_grid.dtype,
        crs='EPSG:4326',
        transform=transform,
    ) as dst:
        dst.write(rain_grid, 1)

    print(f"[Generated] Synthetic cloudburst rain grid saved to: {output_path}")

if __name__ == "__main__":
    generate_synthetic_rain_grid()