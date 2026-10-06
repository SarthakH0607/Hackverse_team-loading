"""
scripts/make_overlay.py
-----------------------
Convert data/change_mask.tif and data/confidence.tif into an RGBA transparent PNG:
  - Red where changed (mask == 1)
  - Alpha = 0 elsewhere (mask == 0)
  - Alpha scaled by confidence (0..255)
  - Output: data/change_overlay.png
  - Print geographic bounds as [west, south, east, north]
"""

from pathlib import Path
import numpy as np
import rasterio
from PIL import Image

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MASK_PATH = DATA_DIR / "change_mask.tif"
CONFIDENCE_PATH = DATA_DIR / "confidence.tif"
OVERLAY_PNG = DATA_DIR / "change_overlay.png"


def main():
    print("=" * 60)
    print("Generating Transparent Change Overlay PNG")
    print("=" * 60)

    if not MASK_PATH.exists():
        raise FileNotFoundError(f"Missing change mask raster: {MASK_PATH}")
    if not CONFIDENCE_PATH.exists():
        raise FileNotFoundError(f"Missing confidence raster: {CONFIDENCE_PATH}")

    # 1. Read Change Mask & Confidence Rasters
    with rasterio.open(MASK_PATH) as mask_src:
        mask = mask_src.read(1)
        bounds = mask_src.bounds
        crs = mask_src.crs
        height, width = mask.shape

    with rasterio.open(CONFIDENCE_PATH) as conf_src:
        confidence = conf_src.read(1).astype(np.float32)

    # 2. Build RGBA Array
    rgba = np.zeros((height, width, 4), dtype=np.uint8)

    changed = (mask == 1)

    # Set Red Channel for changed pixels
    rgba[changed, 0] = 235  # Bright Red
    rgba[changed, 1] = 30   # Green
    rgba[changed, 2] = 30   # Blue

    # Alpha channel: scaled by confidence (minimum visible alpha for detected pixels ~60 to 255)
    conf_clipped = np.clip(confidence, 0.0, 1.0)
    # Scale confidence to [70, 255] for changed pixels so subtle changes are still clearly visible
    alpha_scaled = (70 + conf_clipped * 185).astype(np.uint8)
    rgba[changed, 3] = alpha_scaled[changed]

    # 3. Save as Transparent PNG
    img = Image.fromarray(rgba, mode="RGBA")
    OVERLAY_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(OVERLAY_PNG, format="PNG", optimize=True)
    print(f"Saved transparent overlay: {OVERLAY_PNG}")
    print(f"Image Dimensions: {width} x {height} px")
    print(f"Total Changed Pixels: {np.sum(changed):,}")

    # 4. Print Geographic Bounds as [west, south, east, north]
    west = float(bounds.left)
    south = float(bounds.bottom)
    east = float(bounds.right)
    north = float(bounds.top)
    geo_bounds = [round(west, 6), round(south, 6), round(east, 6), round(north, 6)]

    print("\n" + "=" * 60)
    print(f"Geographic Bounds [west, south, east, north]:")
    print(f"{geo_bounds}")
    print("=" * 60)


if __name__ == "__main__":
    main()
