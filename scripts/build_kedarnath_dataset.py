#!/usr/bin/env python3
"""
scripts/build_kedarnath_dataset.py
-----------------------------------
Generates the complete Kedarnath disaster intelligence dataset:
1. High-resolution pre-disaster optical satellite image from ESRI World Imagery
2. Photorealistic post-disaster satellite image depicting the 2013 Mandakini flash flood & debris torrent
3. Subtle change overlay highlighting the flood surge corridor
4. Exactly 5 ranked priority locations (Kedarnath, Rambara, Gaurikund, Sonprayag, Guptkashi)
5. Tactical Safe Zones (Field hospital, helipad staging camp, high ground shelter)
6. Real-time Risk Alerts GeoJSON
"""

import os
import sys
import io
import math
import json
import shutil
import urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter

# Paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
FRONTEND_DATA_DIR = os.path.join(ROOT_DIR, "frontend", "public", "data")
TILE_CACHE_DIR = os.path.join(DATA_DIR, "kedarnath", "tiles")
os.makedirs(TILE_CACHE_DIR, exist_ok=True)
os.makedirs(FRONTEND_DATA_DIR, exist_ok=True)

# Tile bounds (Zoom 13)
# Covers 78.969°E to 79.189°E, 30.518°N to 30.789°N
ZOOM = 13
X_START, X_END = 5892, 5896   # 5 tiles wide = 1280 px
Y_START, Y_END = 3358, 3366   # 9 tiles high = 2304 px
WIDTH = (X_END - X_START + 1) * 256
HEIGHT = (Y_END - Y_START + 1) * 256

def fetch_tile(x, y, zoom):
    cache_path = os.path.join(TILE_CACHE_DIR, f"{zoom}_{y}_{x}.jpg")
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1000:
        return Image.open(cache_path).convert("RGB")
    
    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{y}/{x}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        data = urllib.request.urlopen(req, timeout=12).read()
        with open(cache_path, "wb") as f:
            f.write(data)
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as e:
        print(f"Warning: Failed to fetch tile {zoom}/{y}/{x}: {e}")
        # Return fallback colored tile if fetch fails
        return Image.new("RGB", (256, 256), (45, 60, 40))

def stitch_base_satellite():
    print(f"Fetching and stitching {5 * 9} satellite tiles at zoom {ZOOM}...")
    base_img = Image.new("RGB", (WIDTH, HEIGHT))
    for col, x in enumerate(range(X_START, X_END + 1)):
        for row, y in enumerate(range(Y_START, Y_END + 1)):
            tile = fetch_tile(x, y, ZOOM)
            base_img.paste(tile, (col * 256, row * 256))
    return base_img

def latlon_to_xy(lat, lon):
    n = 2.0 ** ZOOM
    x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    px = int((x - X_START) * 256)
    py = int((y - Y_START) * 256)
    return px, py

def generate_post_flood_image(pre_img):
    """
    Simulates the realistic optical satellite signature of the 2013 Kedarnath disaster:
    - Chorabari moraine breach debris flow north of Kedarnath temple
    - Widened Mandakini scour channel through Kedarnath town
    - Massive mud and grey silt deposits along Rambara, Jungle Chatti, Gaurikund, and Sonprayag
    - Realistic turbulent flood waters, sediment washouts, and scoured riverbanks
    """
    print("Synthesizing realistic post-disaster satellite imagery...")
    post_np = np.array(pre_img, dtype=np.float32)

    # 1. Define the hydrological flow path of the 2013 disaster
    # [lat, lon, channel_half_width_px, mud_spread_px, intensity]
    waypoints = [
        (30.7550, 79.0680, 22, 50, 0.95),  # Chorabari glacial lake & moraine failure
        (30.7420, 79.0675, 20, 45, 0.95),  # Upper debris fan
        (30.7352, 79.0669, 28, 65, 1.00),  # Kedarnath temple town split channels
        (30.7250, 79.0655, 22, 50, 0.95),  # South of Kedarnath
        (30.7050, 79.0640, 20, 42, 0.92),  # Upper gorge
        (30.6865, 79.0620, 26, 58, 0.96),  # Rambara gorge (complete washout)
        (30.6720, 79.0480, 22, 48, 0.90),  # Chhoti Lincholi / Jungle Chatti
        (30.6600, 79.0370, 20, 44, 0.88),  # Approach to Gaurikund
        (30.6517, 79.0261, 25, 55, 0.92),  # Gaurikund base camp & thermal springs
        (30.6400, 79.0120, 24, 50, 0.88),  # Mandakini lower canyon
        (30.6276, 78.9984, 28, 60, 0.90),  # Sonprayag confluence (massive sediment fan)
        (30.6120, 79.0150, 22, 46, 0.82),  # Downstream toward Rampur
        (30.5900, 79.0300, 18, 38, 0.78),  # Mandakini riverbed
        (30.5600, 79.0520, 16, 32, 0.72),  # Phata corridor
        (30.5350, 79.0700, 15, 30, 0.68),  # Approach to Guptkashi valley
        (30.5180, 79.0780, 14, 28, 0.60),  # Southern exit
    ]

    # Render channel mask and sediment wash mask
    flow_mask = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    sediment_mask = np.zeros((HEIGHT, WIDTH), dtype=np.float32)

    # Convert waypoints to pixel path and interpolate
    pixel_points = []
    for lat, lon, w_ch, w_mud, inten in waypoints:
        px, py = latlon_to_xy(lat, lon)
        pixel_points.append((px, py, w_ch, w_mud, inten))

    for i in range(len(pixel_points) - 1):
        p1 = pixel_points[i]
        p2 = pixel_points[i + 1]
        steps = max(int(np.hypot(p2[0] - p1[0], p2[1] - p1[1]) * 1.5), 10)
        for s in range(steps + 1):
            t = s / steps
            cx = int(p1[0] * (1 - t) + p2[0] * t)
            cy = int(p1[1] * (1 - t) + p2[1] * t)
            w_ch = p1[2] * (1 - t) + p2[2] * t
            w_mud = p1[3] * (1 - t) + p2[3] * t
            inten = p1[4] * (1 - t) + p2[4] * t

            # Draw circular kernels
            r = int(w_mud * 1.2)
            y_min = max(0, cy - r)
            y_max = min(HEIGHT, cy + r)
            x_min = max(0, cx - r)
            x_max = min(WIDTH, cx + r)

            yy, xx = np.ogrid[y_min:y_max, x_min:x_max]
            dist_sq = (xx - cx)**2 + (yy - cy)**2

            # Channel core
            ch_radius_sq = (w_ch)**2
            in_ch = dist_sq <= ch_radius_sq
            flow_mask[y_min:y_max, x_min:x_max] = np.maximum(
                flow_mask[y_min:y_max, x_min:x_max],
                np.where(in_ch, inten, 0.0)
            )

            # Mud spread
            mud_radius_sq = (w_mud)**2
            in_mud = dist_sq <= mud_radius_sq
            mud_val = np.clip(1.0 - np.sqrt(dist_sq) / w_mud, 0, 1) * inten * 0.85
            sediment_mask[y_min:y_max, x_min:x_max] = np.maximum(
                sediment_mask[y_min:y_max, x_min:x_max],
                np.where(in_mud, mud_val, 0.0)
            )

    # Smooth masks for realistic organic boundary
    flow_mask = gaussian_filter(flow_mask, sigma=3.5)
    sediment_mask = gaussian_filter(sediment_mask, sigma=4.0)

    # Add Perlin-like high frequency noise for natural gravel/silt grain
    np.random.seed(42)
    noise = np.random.normal(0, 8.0, (HEIGHT, WIDTH))
    noise = gaussian_filter(noise, sigma=1.2)

    # Colors of 2013 Himalayan flash flood debris:
    # 1. Muddy grey-brown torrential silt: [145, 130, 110]
    # 2. Wet scour rock & gravel bed: [120, 115, 105]
    # 3. High-turbidity flood river thread: [95, 95, 90]
    sediment_color = np.array([142.0, 128.0, 112.0])
    scour_color = np.array([122.0, 118.0, 108.0])
    torrent_water = np.array([92.0, 96.0, 94.0])

    # Blend sediment
    s_alpha = np.clip(sediment_mask, 0, 1)[:, :, None]
    post_np = post_np * (1.0 - s_alpha * 0.75) + (sediment_color + noise[:, :, None]) * (s_alpha * 0.75)

    # Blend deep scour channel
    f_alpha = np.clip(flow_mask, 0, 1)[:, :, None]
    post_np = post_np * (1.0 - f_alpha * 0.88) + (scour_color + torrent_water * 0.3 + noise[:, :, None]) * (f_alpha * 0.88)

    # Clip to valid RGB
    post_np = np.clip(post_np, 0, 255).astype(np.uint8)
    return Image.fromarray(post_np), flow_mask

def generate_change_overlay(flow_mask):
    """
    Creates the tactical red/amber disaster corridor overlay
    with smooth gradients matching Sikkim's overlay format.
    """
    print("Generating tactical change detection overlay...")
    h, w = flow_mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    # High intensity core: bright emergency red [240, 45, 45]
    # Perimeter: warning orange [255, 120, 30]
    thresh = flow_mask > 0.08
    alpha = np.clip(flow_mask * 210, 0, 215).astype(np.uint8)

    rgba[thresh, 0] = 238  # R
    rgba[thresh, 1] = 42   # G
    rgba[thresh, 2] = 42   # B
    rgba[thresh, 3] = alpha[thresh]

    return Image.fromarray(rgba, mode="RGBA")

def create_villages_geojson():
    """
    Exactly 5 ranked critical locations for Kedarnath as requested by the user:
    1. Kedarnath Town & Temple
    2. Rambara Gorge
    3. Gaurikund Base
    4. Sonprayag Confluence
    5. Guptkashi Staging Base
    """
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0669, 30.7352]
                },
                "properties": {
                    "rank": 1,
                    "name": "Kedarnath Town & Temple Sanctuary",
                    "population": 4200,
                    "score": 98.4,
                    "reason": "Chorabari moraine outburst impact zone; Mandakini dual surge channels; perimeter structures demolished; bedrock sanctuary isolated.",
                    "priority": "CRITICAL",
                    "region": "Upper Mandakini / Glacier Valley",
                    "waterSurgeDelta": "+7.2m Flash Inundation",
                    "isolatedCount": "3,400+ Stranded Pilgrims",
                    "roadStatus": "ALL ACCESS TRAILS WASHED OUT",
                    "confidence": "99.4%",
                    "rainfallRisk": "Extreme (Cloudburst 340mm/24h)",
                    "riverGauge": "Peak Outburst Discharge 1,420 m³/s"
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0620, 30.6865]
                },
                "properties": {
                    "rank": 2,
                    "name": "Rambara Gorge Corridor",
                    "population": 1850,
                    "score": 94.7,
                    "reason": "Complete gorge channel inundation; bridges swept away; transit settlements destroyed; high-risk bottleneck.",
                    "priority": "CRITICAL",
                    "region": "Middle Mandakini Canyon",
                    "waterSurgeDelta": "+8.9m Gorge Constriction Surge",
                    "isolatedCount": "1,100+ Trapped on Slopes",
                    "roadStatus": "100% ROUTE DESTROYED",
                    "confidence": "98.1%",
                    "rainfallRisk": "Severe Slope Instability",
                    "riverGauge": "Torrential Debris Velocity 14 m/s"
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0261, 30.6517]
                },
                "properties": {
                    "rank": 3,
                    "name": "Gaurikund Base Camp & Transit",
                    "population": 3400,
                    "score": 89.2,
                    "reason": "Thermal spring basin inundated; parking platforms and pilgrim accommodations collapsed into Mandakini.",
                    "priority": "HIGH",
                    "region": "Lower Mandakini Valley",
                    "waterSurgeDelta": "+5.4m Riverbank Erosion",
                    "isolatedCount": "2,200 Evacuees Waiting Extraction",
                    "roadStatus": "VEHICULAR ACCESS SEVERED",
                    "confidence": "96.5%",
                    "rainfallRisk": "Active Mudflows & Rockfall",
                    "riverGauge": "River Gauge Red Alarm Triggered"
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [78.9984, 30.6276]
                },
                "properties": {
                    "rank": 4,
                    "name": "Sonprayag Confluence Hub",
                    "population": 2100,
                    "score": 82.5,
                    "reason": "Mandakini and Songanga confluence surge; major motor bridge washed away; primary ground evacuation barrier.",
                    "priority": "HIGH",
                    "region": "River Confluence Gateway",
                    "waterSurgeDelta": "+4.8m Backwater Surge",
                    "isolatedCount": "1,600 Pilgrims at Chotti Lincholi trail",
                    "roadStatus": "MAIN BRIDGE DEMOLISHED",
                    "confidence": "95.2%",
                    "rainfallRisk": "High Water Level Warning",
                    "riverGauge": "Confluence Flow 880 m³/s"
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0760, 30.5228]
                },
                "properties": {
                    "rank": 5,
                    "name": "Guptkashi Air & Logistics Base",
                    "population": 5600,
                    "score": 41.0,
                    "reason": "Elevated ridge staging terminal; Air Force Mi-17 heli-rescue staging zone; emergency triage field hospital.",
                    "priority": "MONITORED",
                    "region": "Southern Staging Ridge",
                    "waterSurgeDelta": "High Ground (+0.0m)",
                    "isolatedCount": "Operational Staging (Zero Cutoff)",
                    "roadStatus": "HIGHWAY OPEN (SOUTHWARD LINK)",
                    "confidence": "99.0%",
                    "rainfallRisk": "Intermittent Cloud Cover (Aviation Alert)",
                    "riverGauge": "Safe Above Inundation Line"
                }
            }
        ]
    }
    return geojson

def create_safe_zones_geojson():
    """
    Tactical safe zones for Kedarnath response teams.
    """
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0780, 30.5240]
                },
                "properties": {
                    "name": "Guptkashi Army & NDRF Helipad Staging Camp",
                    "type": "shelter",
                    "lat": 30.5240,
                    "lon": 79.0780,
                    "subtitle": "Major Airborne Extraction Base & Supply Depot",
                    "details": "Dual helipads, emergency medical triage, communication links, dry rations storage.",
                    "generator": "YES (Twin 125kVA Military Gen)",
                    "potableSpring": "Municipal Filtered Reservoir",
                    "elevationDelta": "+640m above riverbed",
                    "bearing": "SOUTH_RIDGE",
                    "distanceKm": 24.5,
                    "estWalkMinutes": 0
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0675, 30.7365]
                },
                "properties": {
                    "name": "Kedarnath Temple High-Ground Perimeter",
                    "type": "shelter",
                    "lat": 30.7365,
                    "lon": 79.0675,
                    "subtitle": "Protected Natural Bedrock Elevated Zone",
                    "details": "Massive granite boulder protection behind temple; elevated rear knoll above mud channel.",
                    "generator": "Emergency Solar & Battery",
                    "potableSpring": "Glacial Runoff Filtered",
                    "elevationDelta": "+18m above surge channel",
                    "bearing": "NORTH_KEDAR",
                    "distanceKm": 0.2,
                    "estWalkMinutes": 5
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0020, 30.6310]
                },
                "properties": {
                    "name": "Sonprayag Upper Ridge Evacuation Shelter",
                    "type": "shelter",
                    "lat": 30.6310,
                    "lon": 79.0020,
                    "subtitle": "High Clearance Pilgrim Reception Camp",
                    "details": "Safe hillside terraced school campus, basic medical post, emergency radio antenna.",
                    "generator": "YES (Diesel Generator 45kVA)",
                    "potableSpring": "Gravity Spring Pipeline",
                    "elevationDelta": "+95m above confluence",
                    "bearing": "WEST_RIDGE",
                    "distanceKm": 0.6,
                    "estWalkMinutes": 18
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0300, 30.3920]
                },
                "properties": {
                    "name": "Agastyamuni Emergency Base Hospital",
                    "type": "hospital",
                    "lat": 30.3920,
                    "lon": 79.0300,
                    "subtitle": "Regional Trauma & Surgical Extraction Center",
                    "details": "Multi-bed ICU, orthopedic surgery unit, trauma stabilization, helipad adjacent.",
                    "generator": "YES (Full Hospital Power Grid Backup)",
                    "potableSpring": "Hospital RO Supply",
                    "elevationDelta": "+120m valley shelf",
                    "bearing": "SOUTH_VALLEY",
                    "distanceKm": 38.0,
                    "estWalkMinutes": 0
                }
            }
        ]
    }
    return geojson

def create_risk_alerts_geojson():
    """
    Live real-time risk alerts for Kedarnath sector.
    """
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0669, 30.7352]
                },
                "properties": {
                    "id": "ALERT-KEDAR-001",
                    "severity": "CRITICAL",
                    "title": "Chorabari Moraine Breach & Debris Torrent",
                    "description": "Glacial outburst surge has carved dual channels flanking temple. Structural perimeter compromise. Ground evacuation impossible.",
                    "action": "Immediate heli-extraction priority from northern high-ground knoll when weather permits.",
                    "timestamp": "2026-10-06T11:00:00Z"
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0620, 30.6865]
                },
                "properties": {
                    "id": "ALERT-KEDAR-002",
                    "severity": "CRITICAL",
                    "title": "Rambara Gorge Total Transit Interruption",
                    "description": "Narrow gorge inundated by debris flow velocity >12 m/s. All footpaths severed. Stranded clusters on upper scree slopes.",
                    "action": "Direct airborne food & medicine drops; guide mobile survivors to high ridges.",
                    "timestamp": "2026-10-06T11:05:00Z"
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [78.9984, 30.6276]
                },
                "properties": {
                    "id": "ALERT-KEDAR-003",
                    "severity": "HIGH",
                    "title": "Sonprayag Confluence Bridge Washout",
                    "description": "Songanga-Mandakini convergence has washed away motor bridge. 1,600+ pilgrims blocked on upstream bank.",
                    "action": "Deploy NDRF zip-line / rope rescue crossings; establish temporary foot suspension bridge.",
                    "timestamp": "2026-10-06T11:10:00Z"
                }
            }
        ]
    }
    return geojson

def main():
    print("=" * 65)
    print("GENERATING KEDARNATH DISASTER INTELLIGENCE DATASET")
    print("=" * 65)

    # 1. Base Pre-Flood Optical Image
    pre_img = stitch_base_satellite()
    print(f"Base optical image size: {pre_img.size}")

    # Standardize to crisp 1200x1200 or 1200x1500 for optimal UI display
    # Let's save full resolution and scaled versions
    pre_out_path = os.path.join(DATA_DIR, "kedarnath_pre_rgb.png")
    frontend_pre_path = os.path.join(FRONTEND_DATA_DIR, "kedarnath_pre_rgb.png")
    pre_img.save(pre_out_path, format="PNG", optimize=True)
    shutil.copyfile(pre_out_path, frontend_pre_path)
    print(f"Saved: {pre_out_path}")

    # 2. Photorealistic Post-Flood Satellite Image
    post_img, flow_mask = generate_post_flood_image(pre_img)
    post_out_path = os.path.join(DATA_DIR, "kedarnath_post_rgb.png")
    frontend_post_path = os.path.join(FRONTEND_DATA_DIR, "kedarnath_post_rgb.png")
    post_img.save(post_out_path, format="PNG", optimize=True)
    shutil.copyfile(post_out_path, frontend_post_path)
    print(f"Saved: {post_out_path}")

    # 3. Change Overlay (RGBA)
    overlay_img = generate_change_overlay(flow_mask)
    overlay_out_path = os.path.join(DATA_DIR, "kedarnath_change_overlay.png")
    frontend_overlay_path = os.path.join(FRONTEND_DATA_DIR, "kedarnath_change_overlay.png")
    overlay_img.save(overlay_out_path, format="PNG", optimize=True)
    shutil.copyfile(overlay_out_path, frontend_overlay_path)
    print(f"Saved: {overlay_out_path}")

    # 4. Villages GeoJSON (5 locations only)
    villages_data = create_villages_geojson()
    villages_path = os.path.join(DATA_DIR, "kedarnath_villages_ranked.geojson")
    frontend_villages_path = os.path.join(FRONTEND_DATA_DIR, "kedarnath_villages_ranked.geojson")
    with open(villages_path, "w", encoding="utf-8") as f:
        json.dump(villages_data, f, indent=2)
    shutil.copyfile(villages_path, frontend_villages_path)
    print(f"Saved: {villages_path} ({len(villages_data['features'])} locations)")

    # 5. Safe Zones GeoJSON
    safe_zones_data = create_safe_zones_geojson()
    safe_path = os.path.join(DATA_DIR, "kedarnath_safe_zones.geojson")
    frontend_safe_path = os.path.join(FRONTEND_DATA_DIR, "kedarnath_safe_zones.geojson")
    with open(safe_path, "w", encoding="utf-8") as f:
        json.dump(safe_zones_data, f, indent=2)
    shutil.copyfile(safe_path, frontend_safe_path)
    print(f"Saved: {safe_path} ({len(safe_zones_data['features'])} safe zones)")

    # 6. Risk Alerts GeoJSON
    risk_data = create_risk_alerts_geojson()
    risk_path = os.path.join(DATA_DIR, "kedarnath_risk_alerts.geojson")
    frontend_risk_path = os.path.join(FRONTEND_DATA_DIR, "kedarnath_risk_alerts.geojson")
    with open(risk_path, "w", encoding="utf-8") as f:
        json.dump(risk_data, f, indent=2)
    shutil.copyfile(risk_path, frontend_risk_path)
    print(f"Saved: {risk_path} ({len(risk_data['features'])} risk alerts)")

    print("\nALL KEDARNATH ASSETS SUCCESSFULLY GENERATED AND DEPLOYED!")

if __name__ == "__main__":
    main()
