"""
scripts/inspect_rasters.py
--------------------------
Inspect metadata for project raster GeoTIFF files:
  - data/sikkim_pre.tif
  - data/sikkim_post.tif
  - data/sikkim_diff.tif
  - data/sikkim_srtm.tif
"""

from pathlib import Path
import rasterio

RASTER_FILES = [
    "data/sikkim_pre.tif",
    "data/sikkim_post.tif",
    "data/sikkim_diff.tif",
    "data/sikkim_srtm.tif",
]

def inspect_raster(rel_path: str):
    path = Path(__file__).resolve().parent.parent / rel_path
    if not path.exists():
        print(f"File not found: {rel_path}\n")
        return

    with rasterio.open(path) as src:
        transform = src.transform
        pixel_size_x = transform.a
        pixel_size_y = transform.e
        
        print("=" * 60)
        print(f"File:       {rel_path}")
        print("=" * 60)
        print(f"Shape:      {src.shape} (bands: {src.count})")
        print(f"CRS:        {src.crs}")
        print(f"Pixel Size: (dx={pixel_size_x:.8f}, dy={pixel_size_y:.8f})")
        print(f"Bounds:     left={src.bounds.left:.6f}, bottom={src.bounds.bottom:.6f}, right={src.bounds.right:.6f}, top={src.bounds.top:.6f}")
        print(f"Dtype:      {src.dtypes[0]}")
        print(f"NoData:     {src.nodata}")
        print()

def main():
    print("Inspecting Project Rasters:\n")
    for r_file in RASTER_FILES:
        inspect_raster(r_file)

if __name__ == "__main__":
    main()
