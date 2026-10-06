#!/usr/bin/env python3
"""
site_config.py - Centralized configuration for disaster intelligence analysis scripts.
Single source of truth for site name, bounding box, event dates, coordinate systems, and paths.
Switch ACTIVE_SITE at the top to toggle between active disaster sites.
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# ACTIVE SITE SELECTION
# =============================================================================
# Set to "sikkim" or "kedarnath"
ACTIVE_SITE = "kedarnath"

SITES = {
    # -------------------------------------------------------------------------
    # Site 1: Sikkim Flash Flood & GLOF (October 2023)
    # -------------------------------------------------------------------------
    "sikkim": {
        "name": "sikkim",
        "display_name": "Sikkim Teesta Valley Flash Flood (Oct 2023)",
        "event_type": "South Lhonak Glacial Lake Outburst Flood (GLOF) & Flash Flood",
        "event_date": "04 Oct 2023",
        "pre_event_dates": "15 Sep - 02 Oct 2023",
        "post_event_dates": "05 Oct - 15 Oct 2023",
        "satellite": "Sentinel-1 (SAR / Radar C-band, VV Polarization)",

        # Spatial bounds & projection (west, south, east, north)
        "bbox": (88.30, 27.15, 88.75, 27.75),
        "utm_epsg": "EPSG:32645",              # UTM Zone 45N for Sikkim
        "center_lat": 27.45,
        "center_lon": 88.52,

        # Input raster files
        "dem_file": "sikkim_srtm.tif",
        "change_mask_file": "change_mask.tif",
        "confidence_file": "confidence.tif",

        # Output filenames
        "safe_zones_file": "safe_zones.geojson",
        "villages_ranked_file": "villages_ranked.geojson",
        "risk_alerts_file": "risk_alerts.geojson",
        "incident_report_file": "incident_report.html",

        # Directory paths
        "data_dir": ROOT_DIR / "data",
        "frontend_dir": ROOT_DIR / "frontend" / "public" / "data",
    },

    # -------------------------------------------------------------------------
    # Site 2: Kedarnath Flash Flood & Debris Flow (June 2013)
    # -------------------------------------------------------------------------
    "kedarnath": {
        "name": "kedarnath",
        "display_name": "Kedarnath Flash Flood & Debris Flow (2013)",
        "event_type": "Chorabari Lake Outburst & Cloudburst Flash Flood",
        "event_date": "16-17 Jun 2013",
        "pre_event_dates": "01 Jun - 14 Jun 2013",
        "post_event_dates": "17 Jun - 25 Jun 2013",
        "satellite": "Landsat-8 (Optical) & Sentinel-1 (Radar)",

        # Spatial bounds & projection (west, south, east, north)
        "bbox": (79.00, 30.60, 79.20, 30.85),
        "utm_epsg": "EPSG:32644",              # UTM Zone 44N for Uttarakhand
        "center_lat": 30.73,
        "center_lon": 79.07,

        # Input raster files
        "dem_file": "kedarnath_srtm.tif",
        "change_mask_file": "kedarnath_change_mask.tif",
        "confidence_file": "kedarnath_confidence.tif",

        # Output filenames (site-prefixed to avoid overwriting Sikkim outputs)
        "safe_zones_file": "kedarnath_safe_zones.geojson",
        "villages_ranked_file": "kedarnath_villages_ranked.geojson",
        "risk_alerts_file": "kedarnath_risk_alerts.geojson",
        "incident_report_file": "kedarnath_incident_report.html",

        # Directory paths
        "data_dir": ROOT_DIR / "data",
        "frontend_dir": ROOT_DIR / "frontend" / "public" / "data",
    }
}

SITE = SITES[ACTIVE_SITE]
KEDARNATH_SITE = SITES["kedarnath"]
SIKKIM_SITE = SITES["sikkim"]
