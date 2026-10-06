#!/usr/bin/env python3
"""
site_config.py - Shared configuration for disaster intelligence analysis scripts.
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

SITE = {
    "name": "sikkim",
    "bbox": (88.30, 27.15, 88.75, 27.75),  # west, south, east, north (lon_min, lat_min, lon_max, lat_max)
    "utm_epsg": "EPSG:32645",              # UTM Zone 45N for Sikkim
    "data_dir": ROOT_DIR / "data",
    "frontend_dir": ROOT_DIR / "frontend" / "public" / "data",
    "dem_file": "sikkim_srtm.tif",
}
