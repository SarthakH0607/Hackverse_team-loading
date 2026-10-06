#!/usr/bin/env python3
"""
scripts/kedarnath_change.py
---------------------------
STAGE 3: Optical Landsat 8 Change Detection (Kedarnath 2013).
Processes multi-band Landsat 8 reflectance (B2=Blue, B3=Green, B4=Red, B5=NIR)
and SRTM DEM to compute NDVI loss and bare-soil exposure.
"""

from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from skimage.morphology import remove_small_objects
from PIL import Image
import matplotlib.pyplot as plt
from site_config import ROOT_DIR, KEDARNATH_SITE

DATA_DIR = KEDARNATH_SITE["data_dir"]
DOCS_DIR = ROOT_DIR / "docs"
TODO_FILE = DOCS_DIR / "A_TODO.md"

PRE_PATH = DATA_DIR / "kedarnath_pre.tif"
POST_PATH = DATA_DIR / "kedarnath_post.tif"
SRTM_PATH = DATA_DIR / KEDARNATH_SITE["dem_file"]

MASK_TIF = DATA_DIR / "kedarnath_change_mask.tif"
CONF_TIF = DATA_DIR / "kedarnath_confidence.tif"
OVERLAY_PNG = DATA_DIR / "kedarnath_overlay.png"
PREVIEW_PNG = DATA_DIR / "kedarnath_preview.png"
PRE_RGB_PNG = DATA_DIR / "kedarnath_pre_rgb.png"
POST_RGB_PNG = DATA_DIR / "kedarnath_post_rgb.png"


def resample_dem(dem_path: Path, match_src: rasterio.DatasetReader) -> np.ndarray:
    with rasterio.open(dem_path) as dem_src:
        dem_data = dem_src.read(1).astype(np.float32)
        if dem_src.nodata is not None:
            dem_data[dem_data == dem_src.nodata] = np.nan
        resampled = np.empty(match_src.shape, dtype=np.float32)
        reproject(
            source=dem_data, destination=resampled,
            src_transform=dem_src.transform, src_crs=dem_src.crs,
            dst_transform=match_src.transform, dst_crs=match_src.crs,
            resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan,
        )
    return resampled


def compute_slope(dem: np.ndarray, transform: rasterio.Affine, lat: float = 30.7) -> np.ndarray:
    dx = abs(transform.a) * 111320.0 * np.cos(np.radians(lat))
    dy = abs(transform.e) * 110540.0
    gy, gx = np.gradient(dem, dy, dx)
    return np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))


def make_rgb(src: rasterio.DatasetReader) -> np.ndarray:
    # Bands B4 (Red, idx 3), B3 (Green, idx 2), B2 (Blue, idx 1)
    r = src.read(3).astype(np.float32)
    g = src.read(2).astype(np.float32)
    b = src.read(1).astype(np.float32)
    # Stretch 0 to 0.3 (or 0 to 3000 if scaled x10000)
    max_val = 3000.0 if np.nanmax(r) > 10.0 else 0.3
    rgb = np.stack([r, g, b], axis=-1) / max_val
    rgb = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    return rgb


def update_todo(missing_files: list):
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    todo_content = "# Project Action Items / Missing Data\n\n"
    if TODO_FILE.exists():
        todo_content = TODO_FILE.read_text(encoding="utf-8")
    
    section_header = "## Stage 3: Missing Kedarnath Optical Datasets\n"
    if section_header not in todo_content:
        todo_content += f"\n{section_header}\n"
    for mf in missing_files:
        line = f"- [ ] Missing: `{mf}` (Expected Landsat 8 surface reflectance B2,B3,B4,B5)\n"
        if line not in todo_content:
            todo_content += line
    TODO_FILE.write_text(todo_content, encoding="utf-8")


def main():
    print("=" * 60)
    print("STAGE 3: Optical Landsat 8 Change Detection (Kedarnath 2013)")
    print("=" * 60)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    required = [("kedarnath_pre.tif", PRE_PATH), ("kedarnath_post.tif", POST_PATH), (KEDARNATH_SITE["dem_file"], SRTM_PATH)]
    missing = [name for name, p in required if not p.exists()]

    if missing:
        print(f"Missing required input files for Kedarnath:\n" + "\n".join(f"  - {m}" for m in missing))
        update_todo(missing)
        print("Logged missing inputs to docs/A_TODO.md. Exiting cleanly.")
        return

    with rasterio.open(PRE_PATH) as pre_src, rasterio.open(POST_PATH) as post_src:
        meta = pre_src.meta.copy()
        bounds = pre_src.bounds
        transform = pre_src.transform

        # Bands: 1=B2 (Blue), 2=B3 (Green), 3=B4 (Red), 4=B5 (NIR)
        pre_b2, pre_b4, pre_b5 = pre_src.read(1).astype(np.float32), pre_src.read(3).astype(np.float32), pre_src.read(4).astype(np.float32)
        post_b2, post_b4, post_b5 = post_src.read(1).astype(np.float32), post_src.read(3).astype(np.float32), post_src.read(4).astype(np.float32)
        pre_rgb = make_rgb(pre_src)
        post_rgb = make_rgb(post_src)

    Image.fromarray(pre_rgb).save(PRE_RGB_PNG)
    Image.fromarray(post_rgb).save(POST_RGB_PNG)

    # Elevation & Slope
    elevation = resample_dem(SRTM_PATH, pre_src)
    slope = compute_slope(elevation, transform, KEDARNATH_SITE.get("center_lat", 30.7))

    # NDVI & Soil proxy
    pre_ndvi = (pre_b5 - pre_b4) / (pre_b5 + pre_b4 + 1e-6)
    post_ndvi = (post_b5 - post_b4) / (post_b5 + post_b4 + 1e-6)
    delta_ndvi = post_ndvi - pre_ndvi

    pre_soil = pre_b4 - pre_b2
    post_soil = post_b4 - post_b2
    delta_soil = post_soil - pre_soil

    valid = np.isfinite(delta_ndvi) & np.isfinite(delta_soil) & np.isfinite(slope)
    flagged = valid & (delta_ndvi < -0.2) & (delta_soil > 0) & (slope <= 30.0)
    change_mask = remove_small_objects(flagged, min_size=20).astype(np.uint8)

    confidence = np.clip(np.abs(delta_ndvi), 0.0, 1.0).astype(np.float32)

    # Save Rasters
    meta.update(count=1, dtype="uint8", nodata=0)
    with rasterio.open(MASK_TIF, "w", **meta) as dst:
        dst.write(change_mask, 1)

    meta.update(count=1, dtype="float32", nodata=np.nan)
    with rasterio.open(CONF_TIF, "w", **meta) as dst:
        dst.write(np.where(valid, confidence, np.nan), 1)

    # Overlay & Preview
    rgba = np.zeros((*change_mask.shape, 4), dtype=np.uint8)
    ch = (change_mask == 1)
    rgba[ch, 0], rgba[ch, 1], rgba[ch, 2] = 235, 30, 30
    rgba[ch, 3] = np.clip(70 + confidence * 185, 0, 255).astype(np.uint8)[ch]
    Image.fromarray(rgba, mode="RGBA").save(OVERLAY_PNG, format="PNG", optimize=True)

    # Preview
    preview = post_rgb.copy()
    preview[ch] = [235, 30, 30]
    Image.fromarray(preview).save(PREVIEW_PNG)

    # Metrics
    dx = abs(transform.a) * 111320.0 * np.cos(np.radians(KEDARNATH_SITE.get("center_lat", 30.7)))
    dy = abs(transform.e) * 110540.0
    px_area_km2 = (dx * dy) / 1e6
    tot_valid = np.sum(valid)
    ch_px = np.sum(ch)

    print(f"Kedarnath Change Flagged: {ch_px:,} px ({(ch_px/tot_valid)*100:.2f}%, {ch_px * px_area_km2:.2f} km2)")
    geo_bounds = [round(float(bounds.left), 6), round(float(bounds.bottom), 6), round(float(bounds.right), 6), round(float(bounds.top), 6)]
    print(f"Overlay Bounds [west, south, east, north]: {geo_bounds}")
    print(">> Note: Snow and cloud coverage can look like change in optical difference analysis.")


if __name__ == "__main__":
    main()
