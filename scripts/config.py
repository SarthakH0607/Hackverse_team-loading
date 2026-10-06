#!/usr/bin/env python3
"""
config.py - Centralized configuration for Disaster Change-Intelligence Analysis.
Easily switch or extend sites (Sikkim 2023, Kedarnath 2013, etc.).
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
FRONTEND_DATA_DIR = ROOT_DIR / "frontend" / "public" / "data"
CACHE_DIR = ROOT_DIR / "cache"

# Ensure essential directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Preconfigured Sites
SITES = {
    "sikkim": {
        "name": "Sikkim Teesta Valley Flash Flood (Oct 2023)",
        "site_id": "sikkim",
        "bbox": (88.30, 27.15, 88.75, 27.75),  # west, south, east, north
        "crs_metric": "EPSG:32645",             # UTM zone 45N
        "dem_file": "sikkim_srtm.tif",
        "pre_event_dates": "15 Sep - 02 Oct 2023",
        "post_event_dates": "05 Oct - 15 Oct 2023",
        "event_date": "04 Oct 2023",
        "event_type": "South Lhonak Glacial Lake Outburst Flood (GLOF) & Flash Flood",
        "satellite": "Sentinel-1 (SAR / Radar C-band, VV Polarization)",
        "center_lat": 27.45,
        "center_lon": 88.52,
    },
    "kedarnath": {
        "name": "Kedarnath Flash Flood & Debris Flow (2013)",
        "site_id": "kedarnath",
        "bbox": (79.00, 30.60, 79.20, 30.85),  # west, south, east, north
        "crs_metric": "EPSG:32644",             # UTM zone 44N
        "dem_file": "kedarnath_srtm.tif",
        "pre_event_dates": "01 Jun - 14 Jun 2013",
        "post_event_dates": "17 Jun - 25 Jun 2013",
        "event_date": "16-17 Jun 2013",
        "event_type": "Chorabari Lake Outburst & Cloudburst Flash Flood",
        "satellite": "Sentinel-1 / Radar",
        "center_lat": 30.73,
        "center_lon": 79.07,
    }
}

# Active Site (default: sikkim)
ACTIVE_SITE = "sikkim"

def get_site_config(site_key: str = ACTIVE_SITE) -> dict:
    return SITES.get(site_key, SITES["sikkim"])

def copy_to_frontend(src_path: Path, filename: str) -> None:
    """Helper to copy generated data outputs to frontend/public/data/ for Person C's web app."""
    try:
        if FRONTEND_DATA_DIR.parent.parent.exists():
            FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
            dst = FRONTEND_DATA_DIR / filename
            import shutil
            shutil.copy2(src_path, dst)
    except Exception:
        pass
