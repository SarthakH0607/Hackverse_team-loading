#!/usr/bin/env python3
"""
scripts/validate.py
-------------------
STAGE 2: Validation of Sikkim change detection results against optional reference extent.
Checks data/reference_sikkim.tif or data/reference_sikkim.geojson. If absent, logs and skips cleanly.
"""

from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio import features
from rasterio.warp import reproject, Resampling
import matplotlib.pyplot as plt
from site_config import SITE

DATA_DIR = SITE["data_dir"]
REF_TIF = DATA_DIR / "reference_sikkim.tif"
REF_GEOJSON = DATA_DIR / "reference_sikkim.geojson"
THRESH_MASK_PATH = DATA_DIR / "change_mask.tif"
ML_MASK_PATH = DATA_DIR / "ml_mask.tif"
VALIDATION_TXT = DATA_DIR / "validation.txt"
VALIDATION_PNG = DATA_DIR / "validation.png"


def compute_metrics(pred: np.ndarray, truth: np.ndarray):
    tp = np.sum((pred == 1) & (truth == 1))
    fp = np.sum((pred == 1) & (truth == 0))
    fn = np.sum((pred == 0) & (truth == 1))
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
    return precision, recall, f1, iou


def main():
    print("=" * 60)
    print("STAGE 2: Change Detection Validation (Sikkim)")
    print("=" * 60)

    # Check for reference extent
    ref_path = None
    if REF_TIF.exists():
        ref_path = REF_TIF
    elif REF_GEOJSON.exists():
        ref_path = REF_GEOJSON

    if ref_path is None:
        msg = "No reference extent found: validation skipped"
        print(msg)
        VALIDATION_TXT.write_text(msg + "\n", encoding="utf-8")
        return

    # Read base radar grid
    if not THRESH_MASK_PATH.exists() or not ML_MASK_PATH.exists():
        print("Error: Missing change_mask.tif or ml_mask.tif for validation.")
        return

    with rasterio.open(THRESH_MASK_PATH) as src:
        thresh_mask = src.read(1).astype(np.uint8)
        shape = src.shape
        transform = src.transform
        crs = src.crs

    with rasterio.open(ML_MASK_PATH) as src:
        ml_mask = src.read(1).astype(np.uint8)

    # Load/Rasterize Reference
    if ref_path.suffix.lower() == ".geojson":
        with open(ref_path, "r", encoding="utf-8") as f:
            gj = json.load(f)
        geoms = [feat["geometry"] for feat in gj.get("features", [])]
        if not geoms:
            ref_mask = np.zeros(shape, dtype=np.uint8)
        else:
            ref_mask = features.rasterize(
                shapes=geoms,
                out_shape=shape,
                transform=transform,
                fill=0,
                default_value=1,
                dtype=np.uint8
            )
    else:
        with rasterio.open(ref_path) as ref_src:
            ref_data = ref_src.read(1).astype(np.float32)
            ref_mask = np.zeros(shape, dtype=np.uint8)
            reproject(
                source=ref_data, destination=ref_mask,
                src_transform=ref_src.transform, src_crs=ref_src.crs,
                dst_transform=transform, dst_crs=crs,
                resampling=Resampling.nearest,
            )
            ref_mask = (ref_mask > 0).astype(np.uint8)

    # Compute Validation Metrics
    p_th, r_th, f1_th, iou_th = compute_metrics(thresh_mask, ref_mask)
    p_ml, r_ml, f1_ml, iou_ml = compute_metrics(ml_mask, ref_mask)

    report_lines = [
        "Validation Results against Reference Extent:",
        f"Reference File: {ref_path.name}",
        f"Reference Changed Pixels: {np.sum(ref_mask == 1):,}",
        "",
        "Threshold Mask (Otsu + Physical Filters):",
        f"  - Precision : {p_th:.4f}",
        f"  - Recall    : {r_th:.4f}",
        f"  - F1-Score  : {f1_th:.4f}",
        f"  - IoU       : {iou_th:.4f}",
        "",
        "ML Mask (Random Forest + Physical Filters):",
        f"  - Precision : {p_ml:.4f}",
        f"  - Recall    : {r_ml:.4f}",
        f"  - F1-Score  : {f1_ml:.4f}",
        f"  - IoU       : {iou_ml:.4f}",
    ]

    report_text = "\n".join(report_lines)
    print(report_text)
    VALIDATION_TXT.write_text(report_text + "\n", encoding="utf-8")

    # Agreement map visualization
    # 0: TN (gray/black), 1: TP (green), 2: FP (red), 3: FN (blue)
    def make_agreement_map(pred, truth):
        cm = np.zeros((*pred.shape, 3), dtype=np.uint8)
        tp = (pred == 1) & (truth == 1)
        fp = (pred == 1) & (truth == 0)
        fn = (pred == 0) & (truth == 1)
        cm[tp] = [46, 204, 113]   # Green
        cm[fp] = [231, 76, 60]    # Red
        cm[fn] = [52, 152, 219]   # Blue
        return cm

    cm_th = make_agreement_map(thresh_mask, ref_mask)
    cm_ml = make_agreement_map(ml_mask, ref_mask)

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    axes[0].imshow(cm_th)
    axes[0].set_title(f"Threshold Mask Agreement\n(P={p_th:.2f}, R={r_th:.2f}, F1={f1_th:.2f}, IoU={iou_th:.2f})")
    axes[0].axis("off")

    axes[1].imshow(cm_ml)
    axes[1].set_title(f"ML Mask Agreement\n(P={p_ml:.2f}, R={r_ml:.2f}, F1={f1_ml:.2f}, IoU={iou_ml:.2f})")
    axes[1].axis("off")

    plt.tight_layout()
    plt.savefig(VALIDATION_PNG, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved validation agreement map to: {VALIDATION_PNG}")


if __name__ == "__main__":
    main()
