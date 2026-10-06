"""
scripts/change_detect.py
------------------------
SAR Change Detection Pipeline:
1. Load Sentinel-1 SAR imagery: sikkim_pre.tif & sikkim_post.tif (VV in dB, band 1)
2. Resample sikkim_srtm.tif to match the SAR raster grid (same shape & transform)
3. Compute slope in degrees from the resampled DEM (metres converted at lat 27.4 deg)
4. Apply 3x3 median filter to reduce speckle on pre and post
5. Compute difference (post - pre) and absolute difference
6. Apply Otsu thresholding (skimage.filters.threshold_otsu)
7. Filter 1: Mask out steep terrain where slope > 30 degrees
8. Filter 2: Mask out permanent water where pre dB < -20
9. Filter 3: Remove small connected blobs < 20 pixels (skimage.morphology.remove_small_objects)
10. Save data/change_mask.tif (uint8, 0 or 1) and data/confidence.tif (float32, 0 to 1)
11. Save data/change_preview.png (red changed pixels overlaid on greyscale post image)
12. Print final percent of area changed and area in square kilometres
"""

from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from scipy.ndimage import median_filter
from skimage.filters import threshold_otsu
from skimage.morphology import remove_small_objects
import matplotlib.pyplot as plt

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRE_PATH = DATA_DIR / "sikkim_pre.tif"
POST_PATH = DATA_DIR / "sikkim_post.tif"
SRTM_PATH = DATA_DIR / "sikkim_srtm.tif"
CHANGE_MASK_TIF = DATA_DIR / "change_mask.tif"
CONFIDENCE_TIF = DATA_DIR / "confidence.tif"
CHANGE_PREVIEW_PNG = DATA_DIR / "change_preview.png"
DIFF_PREVIEW_PNG = DATA_DIR / "diff_filtered_preview.png"


def resample_dem_to_match(src_dem_path: Path, match_src: rasterio.io.DatasetReader) -> np.ndarray:
    """Resample DEM raster to match the target raster grid (shape, CRS, transform)."""
    with rasterio.open(src_dem_path) as dem_src:
        dem_data = dem_src.read(1).astype(np.float32)
        if dem_src.nodata is not None:
            dem_data[dem_data == dem_src.nodata] = np.nan

        resampled_dem = np.empty(match_src.shape, dtype=np.float32)
        reproject(
            source=dem_data,
            destination=resampled_dem,
            src_transform=dem_src.transform,
            src_crs=dem_src.crs,
            dst_transform=match_src.transform,
            dst_crs=match_src.crs,
            resampling=Resampling.bilinear,
            src_nodata=np.nan,
            dst_nodata=np.nan,
        )
    return resampled_dem


def compute_slope_degrees(dem: np.ndarray, transform: rasterio.Affine, center_lat: float = 27.4) -> np.ndarray:
    """Compute terrain slope in degrees using metric pixel dimensions at given latitude."""
    res_x_deg = abs(transform.a)
    res_y_deg = abs(transform.e)

    # Convert degrees to metres at center latitude
    dx = res_x_deg * 111320.0 * np.cos(np.radians(center_lat))
    dy = res_y_deg * 110540.0

    grad_y, grad_x = np.gradient(dem, dy, dx)
    slope_rad = np.arctan(np.sqrt(grad_x**2 + grad_y**2))
    slope_deg = np.degrees(slope_rad)
    return slope_deg


def apply_change_filters(
    pre_arr: np.ndarray,
    post_arr: np.ndarray,
    slope_arr: np.ndarray,
    label: str = "Full",
):
    """
    Compute difference, Otsu threshold, confidence metric, and sequential spatial/physical filters.
    Reports percentage of valid pixels flagged after each step.
    """
    # 1. Clean & median filter (3x3)
    pre_clean = np.where(np.isfinite(pre_arr), pre_arr, np.nan)
    post_clean = np.where(np.isfinite(post_arr), post_arr, np.nan)

    pre_filt = median_filter(pre_clean, size=3)
    post_filt = median_filter(post_clean, size=3)

    # 2. Difference
    diff = post_filt - pre_filt
    abs_diff = np.abs(diff)

    valid_mask = np.isfinite(diff) & np.isfinite(pre_filt) & np.isfinite(post_filt)
    total_valid = np.sum(valid_mask)

    valid_diff = diff[valid_mask]
    diff_min = np.nanmin(valid_diff) if valid_diff.size > 0 else np.nan
    diff_max = np.nanmax(valid_diff) if valid_diff.size > 0 else np.nan
    diff_mean = np.nanmean(valid_diff) if valid_diff.size > 0 else np.nan

    print(f"\n[{label}] Raster Dimensions: {diff.shape}, Valid Pixels: {total_valid:,}")
    print(f"[{label}] Difference (post - pre): Min={diff_min:.4f} dB, Max={diff_max:.4f} dB, Mean={diff_mean:.4f} dB")

    # 3. Otsu Thresholding
    valid_abs_diff = abs_diff[valid_mask]
    otsu_val = threshold_otsu(valid_abs_diff)
    print(f"[{label}] Otsu Threshold: {otsu_val:.4f} dB")

    # Initial Otsu Change Mask
    mask_otsu = valid_mask & (abs_diff > otsu_val)
    cnt_otsu = np.sum(mask_otsu)
    pct_otsu = (cnt_otsu / total_valid) * 100.0
    print(f"[{label}] 1. Initial Otsu Flagged:                {cnt_otsu:,} px ({pct_otsu:.2f}%)")

    # 4. Filter A: Slope <= 30 degrees (mask out steep slope > 30 deg)
    valid_slope = np.isfinite(slope_arr) & (slope_arr <= 30.0)
    mask_slope = mask_otsu & valid_slope
    cnt_slope = np.sum(mask_slope)
    pct_slope = (cnt_slope / total_valid) * 100.0
    print(f"[{label}] 2. After Slope Filter (slope <= 30 deg):   {cnt_slope:,} px ({pct_slope:.2f}%)")

    # 5. Filter B: Permanent Water Mask (mask out pre dB < -20)
    valid_land = pre_filt >= -20.0
    mask_water = mask_slope & valid_land
    cnt_water = np.sum(mask_water)
    pct_water = (cnt_water / total_valid) * 100.0
    print(f"[{label}] 3. After Water Filter (pre >= -20 dB):    {cnt_water:,} px ({pct_water:.2f}%)")

    # 6. Filter C: Remove connected blobs smaller than 20 pixels
    mask_cleaned = remove_small_objects(mask_water.astype(bool), min_size=20)
    cnt_cleaned = np.sum(mask_cleaned)
    pct_cleaned = (cnt_cleaned / total_valid) * 100.0
    print(f"[{label}] 4. After Blob Filter (size >= 20 px):     {cnt_cleaned:,} px ({pct_cleaned:.2f}%)")

    # 7. Confidence metric: absolute distance from Otsu threshold, normalized by 95th percentile, clipped 0..1
    raw_confidence = np.abs(abs_diff - otsu_val)
    valid_conf = raw_confidence[valid_mask]
    p95_conf = np.nanpercentile(valid_conf, 95) if valid_conf.size > 0 else 1.0
    if p95_conf <= 0 or np.isnan(p95_conf):
        p95_conf = 1.0

    confidence = np.clip(raw_confidence / p95_conf, 0.0, 1.0).astype(np.float32)
    confidence[~valid_mask] = 0.0

    return {
        "pre_filt": pre_filt,
        "post_filt": post_filt,
        "diff": diff,
        "abs_diff": abs_diff,
        "mask_otsu": mask_otsu.astype(np.uint8),
        "mask_final": mask_cleaned.astype(np.uint8),
        "confidence": confidence,
        "otsu_val": otsu_val,
        "slope_deg": slope_arr,
        "total_valid": total_valid,
        "changed_count": cnt_cleaned,
        "pct_changed": pct_cleaned,
    }


def save_geotiff(arr: np.ndarray, out_path: Path, src_meta: rasterio.io.DatasetReader, dtype: str):
    """Save array as GeoTIFF preserving matching CRS and affine transform."""
    meta = src_meta.meta.copy()
    meta.update({
        "driver": "GTiff",
        "height": arr.shape[0],
        "width": arr.shape[1],
        "count": 1,
        "dtype": dtype,
        "nodata": None,
        "compress": "lzw",
    })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **meta) as dst:
        dst.write(arr.astype(dtype), 1)
    print(f"Saved GeoTIFF: {out_path} (dtype={dtype}, shape={arr.shape})")


def save_change_overlay_preview(post_arr: np.ndarray, mask: np.ndarray, out_path: Path):
    """Save preview image showing red changed pixels over greyscale post image."""
    # Normalize post image to [0, 1] using robust percentiles
    valid_post = post_arr[np.isfinite(post_arr)]
    p2, p98 = np.nanpercentile(valid_post, 2), np.nanpercentile(valid_post, 98)
    post_norm = np.clip((post_arr - p2) / (p98 - p2 + 1e-6), 0.0, 1.0)
    post_norm = np.nan_to_num(post_norm, nan=0.0)

    # Create RGB grayscale base
    rgb = np.stack([post_norm, post_norm, post_norm], axis=-1)

    # Highlight changed pixels in vibrant red
    changed_pixels = mask == 1
    rgb[changed_pixels, 0] = 1.0  # Red channel
    rgb[changed_pixels, 1] = 0.15 # Green channel
    rgb[changed_pixels, 2] = 0.15 # Blue channel

    plt.figure(figsize=(12, 10), dpi=150)
    plt.imshow(rgb)
    plt.title("Sikkim SAR Disaster Impact: Detected Changes (Red Overlay on Post-Event Sentinel-1)", fontsize=13, pad=12)
    plt.axis("off")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"Saved change overlay preview: {out_path}")


def save_diagnostic_preview(results: dict, out_path: Path):
    """Save 4-panel diagnostic preview image."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 14), dpi=150)

    diff = results["diff"]
    mask_final = results["mask_final"]
    slope = results["slope_deg"]
    conf = results["confidence"]

    # 1. Delta Backscatter
    vmin, vmax = np.nanpercentile(diff, 1), np.nanpercentile(diff, 99)
    im0 = axes[0, 0].imshow(diff, cmap="RdBu_r", vmin=vmin, vmax=vmax)
    fig.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.04, label="dB")
    axes[0, 0].set_title("1. Filtered Difference (Post - Pre)", fontsize=12)

    # 2. Slope Map
    im1 = axes[0, 1].imshow(slope, cmap="terrain", vmin=0, vmax=60)
    fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04, label="Degrees")
    axes[0, 1].set_title("2. SRTM Slope (Degrees)", fontsize=12)

    # 3. Confidence Map
    im2 = axes[1, 0].imshow(conf, cmap="viridis", vmin=0, vmax=1)
    fig.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04, label="Confidence (0-1)")
    axes[1, 0].set_title("3. Change Confidence Map", fontsize=12)

    # 4. Final Filtered Change Mask
    im3 = axes[1, 1].imshow(mask_final, cmap="Reds", vmin=0, vmax=1)
    fig.colorbar(im3, ax=axes[1, 1], fraction=0.046, pad=0.04, label="Flagged (1)")
    axes[1, 1].set_title("4. Final Filtered Damage / Change Mask", fontsize=12)

    for ax in axes.flat:
        ax.set_xlabel("Pixel X")
        ax.set_ylabel("Pixel Y")

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path)
    plt.close()
    print(f"Saved 4-panel diagnostic preview: {out_path}")


def main():
    print("=" * 65)
    print("SAR Change Detection Pipeline: Geotiffs & Confidence Export")
    print("=" * 65)

    # 1. Load Pre and Post images
    print("\n1. Loading SAR GeoTIFFs...")
    with rasterio.open(PRE_PATH) as pre_src, rasterio.open(POST_PATH) as post_src:
        pre_full = pre_src.read(1).astype(np.float32)
        post_full = post_src.read(1).astype(np.float32)

        if pre_src.nodata is not None:
            pre_full[pre_full == pre_src.nodata] = np.nan
        if post_src.nodata is not None:
            post_full[post_full == post_src.nodata] = np.nan

        # 2. Resample DEM to match SAR grid & compute slope
        print("2. Resampling SRTM DEM and computing slope in degrees (lat 27.4 deg)...")
        dem_resampled = resample_dem_to_match(SRTM_PATH, pre_src)
        slope_full = compute_slope_degrees(dem_resampled, pre_src.transform, center_lat=27.4)
        print(f"   Resampled DEM: {dem_resampled.shape}, Slope Range: {np.nanmin(slope_full):.1f} - {np.nanmax(slope_full):.1f} deg")

        # 3. 1000x1000 Crop Test
        print("\n" + "-" * 65)
        print("3. Processing 1000x1000 Crop Test...")
        print("-" * 65)
        crop_slice = (slice(1000, 2000), slice(750, 1750))
        apply_change_filters(
            pre_full[crop_slice],
            post_full[crop_slice],
            slope_full[crop_slice],
            label="1000x1000 Crop",
        )

        # 4. Full Image Processing
        print("\n" + "-" * 65)
        print("4. Processing Full Image...")
        print("-" * 65)
        results = apply_change_filters(
            pre_full,
            post_full,
            slope_full,
            label="Full Image",
        )

        # 5. Export GeoTIFF Products
        print("\n" + "-" * 65)
        print("5. Exporting GeoTIFF Rasters...")
        print("-" * 65)
        save_geotiff(results["mask_final"], CHANGE_MASK_TIF, pre_src, dtype="uint8")
        save_geotiff(results["confidence"], CONFIDENCE_TIF, pre_src, dtype="float32")

        # 6. Save Previews
        print("\n" + "-" * 65)
        print("6. Saving Visual Previews...")
        print("-" * 65)
        save_change_overlay_preview(results["post_filt"], results["mask_final"], CHANGE_PREVIEW_PNG)
        save_diagnostic_preview(results, DIFF_PREVIEW_PNG)

        # 7. Physical Area Calculations
        dx_m = abs(pre_src.transform.a) * 111320.0 * np.cos(np.radians(27.4))
        dy_m = abs(pre_src.transform.e) * 110540.0
        pixel_area_m2 = dx_m * dy_m
        changed_pixels = results["changed_count"]
        total_valid = results["total_valid"]
        area_km2 = (changed_pixels * pixel_area_m2) / 1_000_000.0
        total_area_km2 = (total_valid * pixel_area_m2) / 1_000_000.0

        print("\n" + "=" * 65)
        print("FINAL IMPACT SUMMARY")
        print("=" * 65)
        print(f"  Pixel Dimensions:       {dx_m:.2f} m x {dy_m:.2f} m (Area: {pixel_area_m2:.2f} m2/px)")
        print(f"  Total Valid Study Area: {total_area_km2:.2f} sq km ({total_valid:,} pixels)")
        print(f"  Final Area Changed:     {area_km2:.2f} sq km ({changed_pixels:,} pixels)")
        print(f"  Percent of Area Changed:{results['pct_changed']:.2f}%")
        print("=" * 65)

    print("\nChange Detection Pipeline Complete.")


if __name__ == "__main__":
    main()
