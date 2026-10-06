#!/usr/bin/env python3
"""
risk.py - Weather Risk & Compound Slope Hazard Alert System.

Combines:
  1. Open-Meteo 7-day rainfall forecast (precipitation sum, intensity).
  2. Slope susceptibility calculated from SRTM DEM.
  3. Proximity to active change/flood zones.

Important Disclaimer:
  This produces a "Risk Alert", NOT a deterministic physical prediction.
  Glacial Lake Outburst Floods (GLOFs) and earthquake-triggered landslides are
  not rain-driven; this alert specifically monitors secondary rain-triggered
  landslides, debris reactivation, and residual slope failure hazards.

Output:
  data/risk_alerts.geojson
  data/risk_alerts.json
"""

import json
import os
import sys
import time
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import rowcol
import requests
from shapely.geometry import Point

warnings.filterwarnings("ignore")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SCRIPTS_DIR = ROOT_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
try:
    from config import get_site_config, copy_to_frontend
except ImportError:
    get_site_config = lambda: {
        "bbox": (88.30, 27.15, 88.75, 27.75),
        "dem_file": "sikkim_srtm.tif",
        "center_lat": 27.45,
        "center_lon": 88.52,
    }
    copy_to_frontend = lambda src, fn: None

SITE = get_site_config()
WEST, SOUTH, EAST, NORTH = SITE["bbox"]
DEM_PATH = DATA_DIR / SITE["dem_file"]
VILLAGES_PATH = DATA_DIR / "villages_ranked.geojson"
OUTPUT_GEOJSON = DATA_DIR / "risk_alerts.geojson"
OUTPUT_JSON = DATA_DIR / "risk_alerts.json"


def _log(msg: str) -> None:
    try:
        print(f"[risk_alert] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[risk_alert] {msg.encode('ascii', errors='replace').decode('ascii')}", flush=True)


# -- Open-Meteo Weather Forecast Fetcher --------------------------------------

def fetch_open_meteo_forecast(lat: float, lon: float) -> dict:
    """
    Fetch 7-day weather forecast from Open-Meteo free API (no key required).
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["precipitation_sum", "rain_sum", "precipitation_probability_max", "wind_speed_10m_max"],
        "hourly": ["precipitation", "soil_moisture_0_to_1cm"],
        "timezone": "auto",
        "forecast_days": 7,
    }

    try:
        _log(f"Fetching Open-Meteo forecast for ({lat:.3f}, {lon:.3f})...")
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            precip = daily.get("precipitation_sum", [])
            probs = daily.get("precipitation_probability_max", [])

            total_7d_mm = float(np.sum(precip)) if precip else 0.0
            max_daily_mm = float(np.max(precip)) if precip else 0.0
            max_prob_pct = int(np.max(probs)) if probs else 0

            return {
                "status": "success",
                "total_7d_precip_mm": round(total_7d_mm, 1),
                "max_daily_precip_mm": round(max_daily_mm, 1),
                "max_prob_pct": max_prob_pct,
                "daily_forecast": [
                    {"date": d, "precip_mm": p, "prob_pct": pr}
                    for d, p, pr in zip(dates, precip, probs)
                ],
            }
    except Exception as e:
        _log(f"  [WARN] Open-Meteo request failed: {e}")

    # Fallback simulated seasonal monsoon/post-monsoon estimate
    return {
        "status": "fallback_estimate",
        "total_7d_precip_mm": 48.5,
        "max_daily_precip_mm": 22.0,
        "max_prob_pct": 75,
        "daily_forecast": [],
    }


# -- Slope Susceptibility from DEM --------------------------------------------

def compute_local_slope(dem_path: Path, points: list[Point]) -> list[float]:
    """
    Read SRTM DEM and compute local terrain slope around each village point.
    """
    if not dem_path.exists():
        _log(f"  [WARN] DEM not found at {dem_path}. Using default slope estimates.")
        return [18.0] * len(points)

    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(np.float32)
        transform = src.transform
        nodata = src.nodata

    if nodata is not None:
        dem[dem == nodata] = np.nan

    res_y = abs(transform.e) * 111_320.0
    res_x = abs(transform.a) * 111_320.0 * np.cos(np.radians(27.45))
    grad_y, grad_x = np.gradient(dem, res_y, res_x)
    slope = np.degrees(np.arctan(np.sqrt(grad_x**2 + grad_y**2)))

    slopes = []
    for pt in points:
        try:
            r, c = rowcol(transform, pt.x, pt.y)
            if 0 <= r < slope.shape[0] and 0 <= c < slope.shape[1]:
                val = slope[r, c]
                slopes.append(float(val) if not np.isnan(val) else 15.0)
            else:
                slopes.append(15.0)
        except Exception:
            slopes.append(15.0)

    return slopes


# -- Risk Calculation Pipeline ------------------------------------------------

def evaluate_risk_level(slope_deg: float, forecast_rain_mm: float, affected_fraction: float) -> tuple[str, float, str]:
    """
    Combine slope susceptibility, rainfall threshold, and pre-existing flood damage.
    Returns: (risk_level: 'High'|'Medium'|'Low', risk_score: 0-100, rationale: str)
    """
    # Slope hazard weight (steep terrain > 25° has high landslide risk)
    slope_factor = min(1.0, slope_deg / 35.0)

    # Rainfall trigger weight (heavy rain > 30 mm in 24h triggers Himalayan slope failures)
    rain_factor = min(1.0, forecast_rain_mm / 50.0)

    # Existing destabilization from flood scour
    damage_factor = min(1.0, affected_fraction * 2.0)

    # Composite risk score (0 to 100)
    risk_score = (slope_factor * 35.0 + rain_factor * 40.0 + damage_factor * 25.0)
    risk_score = round(float(np.clip(risk_score, 0.0, 100.0)), 1)

    if risk_score >= 60.0 or (forecast_rain_mm >= 30.0 and slope_deg >= 22.0):
        level = "High"
        action = "High Risk Alert: Impending rainfall on steep/destabilized slopes. Recommend proactive evacuations along gullies."
    elif risk_score >= 35.0:
        level = "Medium"
        action = "Moderate Risk Alert: Possible localized slope slumping and road debris. Monitor access routes."
    else:
        level = "Low"
        action = "Low Risk Alert: Stable topography and low forecast accumulation. Regular monitoring."

    return level, risk_score, action


def main() -> None:
    _log("Starting weather risk alert analysis...")

    # 1. Fetch weather forecast for regional center
    center_lat = SITE.get("center_lat", 27.45)
    center_lon = SITE.get("center_lon", 88.52)
    weather = fetch_open_meteo_forecast(center_lat, center_lon)
    max_rain_mm = weather["max_daily_precip_mm"]
    total_7d_mm = weather["total_7d_precip_mm"]
    _log(f"  Forecast 7-day total rain: {total_7d_mm} mm (Max daily: {max_rain_mm} mm)")

    # 2. Load villages
    if VILLAGES_PATH.exists():
        villages_gdf = gpd.read_file(VILLAGES_PATH)
    else:
        _log(f"  [WARN] {VILLAGES_PATH} not found. Using fallback point grid.")
        villages_gdf = gpd.GeoDataFrame({
            "name": ["Chungthang", "Lachung", "Mangan", "Dikchu", "Singtam"],
            "geometry": [
                Point(88.646, 27.604),
                Point(88.742, 27.689),
                Point(88.531, 27.490),
                Point(88.522, 27.402),
                Point(88.498, 27.234),
            ],
            "affected_fraction": [0.25, 0.20, 0.15, 0.18, 0.12],
            "population": [1500, 6000, 4500, 1200, 8000],
        }, crs="EPSG:4326")

    # 3. Compute slope for each village
    slopes = compute_local_slope(DEM_PATH, list(villages_gdf.geometry))

    # 4. Compute risk alert per village
    results = []
    for idx, row in villages_gdf.iterrows():
        slope = slopes[idx]
        aff_frac = float(row.get("affected_fraction", 0.15))
        level, r_score, rationale = evaluate_risk_level(slope, max_rain_mm, aff_frac)

        results.append({
            "name": row.get("name", f"Location_{idx+1}"),
            "risk_level": level,
            "risk_score": r_score,
            "slope_deg": round(slope, 1),
            "forecast_rain_24h_mm": max_rain_mm,
            "forecast_rain_7d_mm": total_7d_mm,
            "rationale": rationale,
            "population": int(row.get("population", 1000)),
            "geometry": row.geometry,
        })

    alerts_gdf = gpd.GeoDataFrame(results, crs="EPSG:4326")
    alerts_gdf = alerts_gdf.sort_values(by="risk_score", ascending=False).reset_index(drop=True)

    # 5. Save GeoJSON and JSON outputs
    alerts_gdf.to_file(OUTPUT_GEOJSON, driver="GeoJSON")
    copy_to_frontend(OUTPUT_GEOJSON, "risk_alerts.geojson")

    # Save summary JSON with explicit limitations & methodology disclaimer
    summary_data = {
        "title": "Disaster Risk & Weather Alert Summary",
        "site": SITE["name"],
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "disclaimer": (
            "NOTICE: This is an emergency risk alert, NOT a deterministic prediction. "
            "Glacial Lake Outburst Floods (GLOFs) are non-meteorological events. "
            "This alert evaluates secondary rainfall-induced landslide reactivation on destabilized slopes."
        ),
        "weather_summary": weather,
        "counts": {
            "high_risk": int((alerts_gdf["risk_level"] == "High").sum()),
            "medium_risk": int((alerts_gdf["risk_level"] == "Medium").sum()),
            "low_risk": int((alerts_gdf["risk_level"] == "Low").sum()),
            "total_monitored": len(alerts_gdf),
        },
        "top_alerts": alerts_gdf[["name", "risk_level", "risk_score", "slope_deg", "rationale"]].head(10).to_dict(orient="records"),
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    copy_to_frontend(OUTPUT_JSON, "risk_alerts.json")

    _log(f"Saved risk alerts -> {OUTPUT_GEOJSON} and {OUTPUT_JSON}")
    _log(f"Alert summary: High={summary_data['counts']['high_risk']}, Medium={summary_data['counts']['medium_risk']}, Low={summary_data['counts']['low_risk']}")


if __name__ == "__main__":
    main()
