#!/usr/bin/env python3
"""
risk.py - Compound Weather & Slope Susceptibility Risk Alert System.

Fetches live rainfall forecast from Open-Meteo API across the bounding box,
computes slope susceptibility from SRTM DEM, and combines them into regional
risk alert zones (Low, Med, High).

Outputs:
  - data/risk_alerts.geojson
  - frontend/public/data/risk_alerts.geojson
"""

import json
import math
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
from shapely.geometry import box

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "scripts"))

try:
    from scripts.site_config import SITE
except ImportError:
    from site_config import SITE

# ==============================================================================
# NAMED THRESHOLD CONSTANTS & CONFIGURATION
# ==============================================================================
GRID_ROWS = 3
GRID_COLS = 3
FORECAST_DAYS = 3

# Slope susceptibility thresholds (in degrees)
# Under 15 deg -> Low, 15 to 30 deg -> Med, over 30 deg -> High
SLOPE_LOW_MAX = 15.0
SLOPE_MED_MAX = 30.0

# Rainfall thresholds for 3-day accumulated precipitation (in mm)
# Under 5 mm -> Low, 5 to 20 mm -> Med, over 20 mm -> High
RAIN_LOW_MAX = 5.0
RAIN_MED_MAX = 20.0

# Compound Risk Matrix: (Slope_Class, Rain_Class) -> Risk Level
RISK_MATRIX = {
    ("High", "High"): "High",
    ("High", "Med"):  "High",
    ("High", "Low"):  "Med",
    ("Med",  "High"): "High",
    ("Med",  "Med"):  "Med",
    ("Med",  "Low"):  "Low",
    ("Low",  "High"): "Med",
    ("Low",  "Med"):  "Low",
    ("Low",  "Low"):  "Low",
}

DISCLAIMER_NOTE = (
    "Risk alert, not a prediction. Glacial lake outbursts are not rain-driven and are not covered."
)

# Paths strictly from site_config
DATA_DIR = Path(SITE["data_dir"])
FRONTEND_DIR = Path(SITE["frontend_dir"])
DEM_PATH = DATA_DIR / SITE["dem_file"]
RISK_GEOJSON_FILENAME = SITE.get("risk_alerts_file", "risk_alerts.geojson" if SITE.get("name") == "sikkim" else f"{SITE.get('name')}_risk_alerts.geojson")
RISK_JSON_FILENAME = RISK_GEOJSON_FILENAME.replace(".geojson", ".json")
OUTPUT_GEOJSON = DATA_DIR / RISK_GEOJSON_FILENAME
OUTPUT_JSON = DATA_DIR / RISK_JSON_FILENAME
FRONTEND_OUTPUT_GEOJSON = FRONTEND_DIR / RISK_GEOJSON_FILENAME
FRONTEND_OUTPUT_JSON = FRONTEND_DIR / RISK_JSON_FILENAME


def classify_slope(slope_deg: float) -> str:
    """Classify terrain slope into Low, Med, or High susceptibility."""
    if slope_deg < SLOPE_LOW_MAX:
        return "Low"
    elif slope_deg <= SLOPE_MED_MAX:
        return "Med"
    else:
        return "High"


def classify_rain(rain_mm: float) -> str:
    """Classify 3-day rainfall into Low, Med, or High intensity."""
    if rain_mm < RAIN_LOW_MAX:
        return "Low"
    elif rain_mm <= RAIN_MED_MAX:
        return "Med"
    else:
        return "High"


def combine_risk(slope_class: str, rain_class: str) -> str:
    """Combine slope susceptibility and forecast rain into final risk rating."""
    return RISK_MATRIX.get((slope_class, rain_class), "Med")


def compute_slope_grid(dem_path: Path, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
    """
    Compute slope from DEM raster and return mean slope per grid cell.
    """
    if not dem_path.exists():
        raise FileNotFoundError(f"DEM raster not found at {dem_path}")

    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(np.float32)
        transform = src.transform
        nodata = src.nodata

    if nodata is not None:
        dem[dem == nodata] = np.nan

    center_lat = (min_lat + max_lat) / 2.0
    res_y = abs(transform.e) * 111_320.0
    res_x = abs(transform.a) * 111_320.0 * np.cos(np.radians(center_lat))
    gy, gx = np.gradient(dem, res_y, res_x)
    slope = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))

    return slope, transform


def fetch_live_rainfall(grid_centers: list[tuple[float, float]]) -> tuple[list[float], str, int, str]:
    """
    Fetch 3-day precipitation forecast from Open-Meteo for grid center points.
    Returns: (rain_totals_mm, exact_url, status_code, timestamp_str)
    """
    url = "https://api.open-meteo.com/v1/forecast"
    lats = [f"{lat:.4f}" for lat, _ in grid_centers]
    lons = [f"{lon:.4f}" for _, lon in grid_centers]

    params = {
        "latitude": ",".join(lats),
        "longitude": ",".join(lons),
        "daily": "precipitation_sum",
        "forecast_days": FORECAST_DAYS,
        "timezone": "auto",
    }

    resp = requests.get(url, params=params, timeout=15)
    exact_url = resp.url
    status_code = resp.status_code

    if status_code != 200:
        raise RuntimeError(f"Open-Meteo API returned HTTP status {status_code}: {resp.text}")

    data = resp.json()
    if isinstance(data, dict):
        data = [data]

    timestamp_str = resp.headers.get("Date", datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"))
    
    # Extract precipitation sum for each point
    rain_totals = []
    for item in data:
        daily_precip = item.get("daily", {}).get("precipitation_sum", [])
        total_mm = float(np.sum(daily_precip)) if daily_precip else 0.0
        rain_totals.append(round(total_mm, 1))

    return rain_totals, exact_url, status_code, timestamp_str


def fallback_stale_result(error_msg: str):
    """
    Fallback handler when live API call fails.
    Uses last saved result and marks notes as stale.
    """
    print(f"\n[ERROR] Open-Meteo live forecast API call failed: {error_msg}")
    print("[FALLBACK] Attempting to fall back to last saved risk alerts...")

    if OUTPUT_GEOJSON.exists():
        with open(OUTPUT_GEOJSON, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        features = saved_data.get("features", [])
        for feat in features:
            props = feat.get("properties", {})
            existing_note = props.get("note", DISCLAIMER_NOTE)
            props["note"] = f"stale (API unavailable): {existing_note}"

        saved_data["features"] = features

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_GEOJSON, "w", encoding="utf-8") as f:
            json.dump(saved_data, f, indent=2)

        FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OUTPUT_GEOJSON, FRONTEND_OUTPUT_GEOJSON)

        print(f"[FALLBACK] Successfully restored last saved data as 'stale' -> {OUTPUT_GEOJSON}")
        
        # Summary counts
        risks = [f["properties"].get("risk") for f in features]
        print(f"Risk Counts (Stale Fallback): Low={risks.count('Low')}, Med={risks.count('Med')}, High={risks.count('High')}")
        return

    raise RuntimeError("No saved risk_alerts.geojson found for stale fallback.")


def main():
    bbox = SITE["bbox"]
    min_lon, min_lat, max_lon, max_lat = bbox

    # 1. Generate 3x3 Grid Polygons & Centers
    dlat = (max_lat - min_lat) / GRID_ROWS
    dlon = (max_lon - min_lon) / GRID_COLS

    zones_geom = []
    grid_centers = []
    zone_names = []

    # Iterate North-to-South (top-down), West-to-East (left-right)
    zone_idx = 1
    for r in reversed(range(GRID_ROWS)):
        for c in range(GRID_COLS):
            c_min_lon = min_lon + c * dlon
            c_max_lon = min_lon + (c + 1) * dlon
            c_min_lat = min_lat + r * dlat
            c_max_lat = min_lat + (r + 1) * dlat

            poly = box(c_min_lon, c_min_lat, c_max_lon, c_max_lat)
            center_lat = (c_min_lat + c_max_lat) / 2.0
            center_lon = (c_min_lon + c_max_lon) / 2.0

            zones_geom.append((poly, c_min_lon, c_min_lat, c_max_lon, c_max_lat))
            grid_centers.append((center_lat, center_lon))
            zone_names.append(f"Zone {zone_idx}")
            zone_idx += 1

    # 2. Fetch Live Weather from Open-Meteo
    try:
        rain_totals_mm, exact_url, status_code, timestamp_str = fetch_live_rainfall(grid_centers)
        print("=" * 80)
        print("LIVE OPEN-METEO WEATHER FORECAST")
        print("=" * 80)
        print(f"Exact API URL Called : {exact_url}")
        print(f"HTTP Response Status : {status_code} OK")
        print(f"Data Timestamp / Date: {timestamp_str}")
        print("=" * 80)
    except Exception as e:
        fallback_stale_result(str(e))
        return

    # 3. Compute Slope from SRTM DEM
    slope_raster, transform = compute_slope_grid(DEM_PATH, min_lon, min_lat, max_lon, max_lat)

    # 4. Build Zone Features
    features = []
    low_count = 0
    med_count = 0
    high_count = 0

    for i, (poly, c_min_lon, c_min_lat, c_max_lon, c_max_lat) in enumerate(zones_geom):
        zone_name = zone_names[i]
        rain_mm = rain_totals_mm[i]

        # Extract raster pixel window for cell
        r_min, c_min = rasterio.transform.rowcol(transform, c_min_lon, c_max_lat)
        r_max, c_max = rasterio.transform.rowcol(transform, c_max_lon, c_min_lat)
        r1, r2 = max(0, min(r_min, r_max)), min(slope_raster.shape[0], max(r_min, r_max))
        c1, c2 = max(0, min(c_min, c_max)), min(slope_raster.shape[1], max(c_min, c_max))

        zone_slope_pixels = slope_raster[r1:r2, c1:c2]
        mean_slope = float(np.nanmean(zone_slope_pixels)) if zone_slope_pixels.size > 0 else 20.0

        # Classifications
        slope_class = classify_slope(mean_slope)
        rain_class = classify_rain(rain_mm)
        risk = combine_risk(slope_class, rain_class)

        if risk == "Low":
            low_count += 1
        elif risk == "Med":
            med_count += 1
        elif risk == "High":
            high_count += 1

        feature = {
            "type": "Feature",
            "properties": {
                "zone": zone_name,
                "risk": risk,
                "rain_mm": rain_mm,
                "slope_class": slope_class,
                "note": DISCLAIMER_NOTE,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [round(c_min_lon, 6), round(c_min_lat, 6)],
                        [round(c_max_lon, 6), round(c_min_lat, 6)],
                        [round(c_max_lon, 6), round(c_max_lat, 6)],
                        [round(c_min_lon, 6), round(c_max_lat, 6)],
                        [round(c_min_lon, 6), round(c_min_lat, 6)],
                    ]
                ],
            },
        }
        features.append(feature)

    geojson_data = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }

    # 5. Write data/risk_alerts.geojson & copy to frontend/public/data/risk_alerts.geojson
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)

    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUTPUT_GEOJSON, FRONTEND_OUTPUT_GEOJSON)

    # Also save complementary JSON summary if needed
    summary_json = {
        "site": SITE.get("name", "sikkim"),
        "timestamp": timestamp_str,
        "api_url": exact_url,
        "counts": {
            "Low": low_count,
            "Med": med_count,
            "High": high_count,
            "Total": len(features),
        },
        "zones": [f["properties"] for f in features],
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary_json, f, indent=2)
    shutil.copyfile(OUTPUT_JSON, FRONTEND_OUTPUT_JSON)

    print(f"\nWritten {OUTPUT_GEOJSON}")
    print(f"Copied to {FRONTEND_OUTPUT_GEOJSON}")
    print(f"\nRisk Level Counts (Total: {len(features)} zones):")
    print(f"  Low : {low_count}")
    print(f"  Med : {med_count}")
    print(f"  High: {high_count}")


if __name__ == "__main__":
    main()
