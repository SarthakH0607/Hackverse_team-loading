#!/usr/bin/env python3
"""
scripts/ml_change.py
--------------------
STAGE 1: Machine Learning SAR Change Detection (Sikkim).
Trains a Random Forest classifier on heuristic weak labels and predicts
per-pixel change probability, generating masks, metrics, comparisons, and overlays.
"""

from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from scipy.ndimage import median_filter, uniform_filter
from skimage.morphology import remove_small_objects
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_fscore_support
import matplotlib.pyplot as plt
from PIL import Image
from site_config import SIKKIM_SITE

DATA_DIR = SIKKIM_SITE["data_dir"]
PRE_PATH = DATA_DIR / "sikkim_pre.tif"
POST_PATH = DATA_DIR / "sikkim_post.tif"
SRTM_PATH = DATA_DIR / SIKKIM_SITE["dem_file"]
BASE_MASK_PATH = DATA_DIR / "change_mask.tif"
PROB_TIF = DATA_DIR / "ml_probability.tif"
ML_MASK_TIF = DATA_DIR / "ml_mask.tif"
COMPARISON_PNG = DATA_DIR / "ml_vs_threshold.png"
OVERLAY_PNG = DATA_DIR / "ml_overlay.png"


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


def compute_slope(dem: np.ndarray, transform: rasterio.Affine, lat: float = 27.4) -> np.ndarray:
    dx = abs(transform.a) * 111320.0 * np.cos(np.radians(lat))
    dy = abs(transform.e) * 110540.0
    gy, gx = np.gradient(dem, dy, dx)
    return np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))


def main():
    print("=" * 60)
    print("STAGE 1: ML-Based SAR Change Detection (Sikkim)")
    print("=" * 60)

    with rasterio.open(PRE_PATH) as pre_src, rasterio.open(POST_PATH) as post_src:
        pre_raw = pre_src.read(1).astype(np.float32)
        post_raw = post_src.read(1).astype(np.float32)
        meta = pre_src.meta.copy()
        bounds = pre_src.bounds
        transform = pre_src.transform

    elevation = resample_dem(SRTM_PATH, pre_src)
    slope = compute_slope(elevation, transform, SITE.get("center_lat", 27.4))

    # 1. Feature Engineering
    pre_filt = median_filter(np.where(np.isfinite(pre_raw), pre_raw, np.nan), size=3)
    post_filt = median_filter(np.where(np.isfinite(post_raw), post_raw, np.nan), size=3)
    diff = post_filt - pre_filt
    abs_diff = np.abs(diff)

    mean_diff_5x5 = uniform_filter(diff, size=5)
    var_diff_5x5 = np.maximum(0.0, uniform_filter(diff**2, size=5) - mean_diff_5x5**2)
    std_diff_5x5 = np.sqrt(var_diff_5x5)

    valid = np.isfinite(pre_filt) & np.isfinite(post_filt) & np.isfinite(diff) & np.isfinite(slope) & np.isfinite(elevation)
    feature_names = ["pre_dB", "post_dB", "diff", "abs_diff", "slope", "elevation", "diff_std_5x5", "diff_mean_5x5"]
    features_stack = np.stack([pre_filt, post_filt, diff, abs_diff, slope, elevation, std_diff_5x5, mean_diff_5x5], axis=-1)

    # 2. Weak Labels
    valid_abs_diff = abs_diff[valid]
    p99 = np.percentile(valid_abs_diff, 99)
    p50 = np.percentile(valid_abs_diff, 50)
    changed_weak = valid & (abs_diff > p99) & (slope < 30.0)
    unchanged_weak = valid & (abs_diff < p50)

    idx_ch = np.flatnonzero(changed_weak)
    idx_unch = np.flatnonzero(unchanged_weak)
    n_samples = min(100000, len(idx_ch) + len(idx_unch))
    n_ch = min(len(idx_ch), n_samples // 2)
    n_unch = min(len(idx_unch), n_samples - n_ch)

    rng = np.random.default_rng(42)
    sample_idx = np.concatenate([rng.choice(idx_ch, size=n_ch, replace=False), rng.choice(idx_unch, size=n_unch, replace=False)])
    rng.shuffle(sample_idx)

    X_flat = features_stack.reshape(-1, len(feature_names))
    X_train_full = X_flat[sample_idx]
    y_train_full = np.concatenate([np.ones(n_ch, dtype=int), np.zeros(n_unch, dtype=int)])

    # 3. Train Classifier & Evaluate Weak Split
    X_tr, X_te, y_tr, y_te = train_test_split(X_train_full, y_train_full, test_size=0.3, random_state=42, stratify=y_train_full)
    rf = RandomForestClassifier(n_estimators=150, max_depth=12, class_weight="balanced", n_jobs=-1, random_state=42)
    rf.fit(X_tr, y_tr)

    preds_te = rf.predict(X_te)
    p, r, f1, _ = precision_recall_fscore_support(y_te, preds_te, average="binary")
    print(f"Weak Label Evaluation (30% split): Precision={p:.4f}, Recall={r:.4f}, F1={f1:.4f}")
    print(">> Note: This metric only measures agreement with heuristic weak labels, not ground truth.")

    # 4. Predict Probabilities in Chunks
    prob_map = np.zeros(valid.shape, dtype=np.float32)
    valid_indices = np.flatnonzero(valid)
    chunk_size = 100000
    for i in range(0, len(valid_indices), chunk_size):
        chunk_idx = valid_indices[i:i + chunk_size]
        prob_map.ravel()[chunk_idx] = rf.predict_proba(X_flat[chunk_idx])[:, 1]

    # Post-filtering for final ML Mask
    raw_ml_mask = (prob_map > 0.5) & (slope < 30.0) & (pre_filt > -20.0)
    ml_mask = remove_small_objects(raw_ml_mask, min_size=20).astype(np.uint8)

    # Save Rasters
    meta.update(dtype="float32", count=1, nodata=np.nan)
    with rasterio.open(PROB_TIF, "w", **meta) as dst:
        dst.write(np.where(valid, prob_map, np.nan), 1)

    meta.update(dtype="uint8", count=1, nodata=0)
    with rasterio.open(ML_MASK_TIF, "w", **meta) as dst:
        dst.write(ml_mask, 1)

    # 5. Metrics & Feature Importances
    dx = abs(transform.a) * 111320.0 * np.cos(np.radians(SITE.get("center_lat", 27.4)))
    dy = abs(transform.e) * 110540.0
    pixel_area_km2 = (dx * dy) / 1e6

    with rasterio.open(BASE_MASK_PATH) as b_src:
        thresh_mask = b_src.read(1).astype(np.uint8)

    total_v = np.sum(valid)
    ml_px = np.sum(ml_mask == 1)
    th_px = np.sum(thresh_mask == 1)
    intersection = np.sum((ml_mask == 1) & (thresh_mask == 1))
    union = np.sum((ml_mask == 1) | (thresh_mask == 1))
    iou = intersection / union if union > 0 else 0.0

    print(f"ML Mask Flagged: {ml_px:,} px ({(ml_px/total_v)*100:.2f}%, {ml_px * pixel_area_km2:.2f} km2)")
    print(f"Threshold Mask Flagged: {th_px:,} px ({(th_px/total_v)*100:.2f}%, {th_px * pixel_area_km2:.2f} km2)")
    print(f"IoU (ML vs Threshold): {iou:.4f}")

    print("\nFeature Importances:")
    sorted_fi = sorted(zip(feature_names, rf.feature_importances_), key=lambda x: x[1], reverse=True)
    for name, imp in sorted_fi:
        print(f"  - {name:15s}: {imp:.4f}")

    # Save Comparison Plot
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    axes[0].imshow(thresh_mask, cmap="Reds")
    axes[0].set_title("Otsu Threshold Mask")
    axes[1].imshow(ml_mask, cmap="Reds")
    axes[1].set_title("Random Forest ML Mask")
    im2 = axes[2].imshow(prob_map, cmap="inferno", vmin=0, vmax=1)
    axes[2].set_title("Change Probability Map")
    plt.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)
    for ax in axes:
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(COMPARISON_PNG, dpi=200, bbox_inches="tight")
    plt.close()

    # 6. Save Transparent RGBA Overlay
    rgba = np.zeros((*ml_mask.shape, 4), dtype=np.uint8)
    ch_idx = (ml_mask == 1)
    rgba[ch_idx, 0] = 235  # Red
    rgba[ch_idx, 1] = 30
    rgba[ch_idx, 2] = 30
    alpha_scaled = np.clip(70 + prob_map * 185, 0, 255).astype(np.uint8)
    rgba[ch_idx, 3] = alpha_scaled[ch_idx]

    Image.fromarray(rgba, mode="RGBA").save(OVERLAY_PNG, format="PNG", optimize=True)
    geo_bounds = [round(float(bounds.left), 6), round(float(bounds.bottom), 6), round(float(bounds.right), 6), round(float(bounds.top), 6)]
    print(f"Saved ML Overlay to: {OVERLAY_PNG}")
    print(f"ML Overlay Bounds [west, south, east, north]: {geo_bounds}")


if __name__ == "__main__":
    main()
