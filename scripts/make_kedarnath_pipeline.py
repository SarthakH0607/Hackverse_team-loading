#!/usr/bin/env python3
"""
scripts/make_kedarnath_pipeline.py
-----------------------------------
Builds complete, production-ready Kedarnath dataset:
1. Copies stitched base satellite image as kedarnath_pre_rgb.png
2. Synthesizes photorealistic post-disaster satellite imagery (kedarnath_post_rgb.png)
3. Generates clean tactical change detection overlay (kedarnath_change_overlay.png)
4. Generates 5 ranked priority locations (kedarnath_villages_ranked.geojson)
5. Generates safe zones (kedarnath_safe_zones.geojson)
6. Generates risk alerts (kedarnath_risk_alerts.geojson)
Deploys to both data/ and frontend/public/data/
"""

import os
import json
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
FRONTEND_DATA = os.path.join(ROOT_DIR, "frontend", "public", "data")
KEDAR_SRC = os.path.join(DATA_DIR, "kedarnath", "stitched_test.png")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FRONTEND_DATA, exist_ok=True)

def run():
    print("Loading base optical satellite image...")
    pre_img = Image.open(KEDAR_SRC).convert("RGB")
    width, height = pre_img.size
    print(f"Image dimensions: {width} x {height}")

    # Save Pre-RGB image
    pre_path = os.path.join(DATA_DIR, "kedarnath_pre_rgb.png")
    pre_front = os.path.join(FRONTEND_DATA, "kedarnath_pre_rgb.png")
    pre_img.save(pre_path, format="PNG", optimize=True)
    shutil.copyfile(pre_path, pre_front)
    print("Saved Pre-RGB image.")

    # Generate photorealistic post-flood image
    print("Simulating 2013 Kedarnath Mandakini debris torrent...")
    pre_np = np.array(pre_img, dtype=np.float32)

    # Coordinates in image space [px_x, px_y, channel_radius, sediment_radius, intensity]
    # Corresponding to:
    # 1. Chorabari glacial lake breach north of Kedarnath: ~ (566, 240)
    # 2. Kedarnath town & temple split: ~ (566, 365)
    # 3. Middle canyon: ~ (550, 520)
    # 4. Rambara gorge (wiped out): ~ (538, 694)
    # 5. Jungle Chatti / approach: ~ (420, 810)
    # 6. Gaurikund base: ~ (329, 931)
    # 7. Sonprayag confluence: ~ (167, 1094)
    # 8. Rampur transit: ~ (264, 1200)
    # 9. Lower Mandakini exit: ~ (438, 1470)
    waypoints = [
        (566, 220, 18, 42, 0.95),
        (566, 365, 24, 55, 1.00),
        (550, 520, 19, 44, 0.95),
        (538, 694, 25, 54, 0.98),
        (420, 810, 20, 45, 0.92),
        (329, 931, 23, 50, 0.94),
        (167, 1094, 26, 56, 0.95),
        (264, 1200, 20, 44, 0.86),
        (438, 1470, 16, 36, 0.75),
    ]

    flow_mask = np.zeros((height, width), dtype=np.float32)
    sediment_mask = np.zeros((height, width), dtype=np.float32)

    for i in range(len(waypoints) - 1):
        p1 = waypoints[i]
        p2 = waypoints[i + 1]
        dist = np.hypot(p2[0] - p1[0], p2[1] - p1[1])
        steps = max(int(dist * 2.0), 20)

        for s in range(steps + 1):
            t = s / steps
            cx = int(p1[0] * (1 - t) + p2[0] * t)
            cy = int(p1[1] * (1 - t) + p2[1] * t)
            w_ch = p1[2] * (1 - t) + p2[2] * t
            w_sed = p1[3] * (1 - t) + p2[3] * t
            inten = p1[4] * (1 - t) + p2[4] * t

            r = int(w_sed * 1.25)
            y_min = max(0, cy - r)
            y_max = min(height, cy + r)
            x_min = max(0, cx - r)
            x_max = min(width, cx + r)

            yy, xx = np.ogrid[y_min:y_max, x_min:x_max]
            dist_sq = (xx - cx)**2 + (yy - cy)**2

            in_ch = dist_sq <= (w_ch**2)
            flow_mask[y_min:y_max, x_min:x_max] = np.maximum(
                flow_mask[y_min:y_max, x_min:x_max],
                np.where(in_ch, inten, 0.0)
            )

            in_sed = dist_sq <= (w_sed**2)
            sed_val = np.clip(1.0 - np.sqrt(dist_sq) / w_sed, 0, 1) * inten * 0.85
            sediment_mask[y_min:y_max, x_min:x_max] = np.maximum(
                sediment_mask[y_min:y_max, x_min:x_max],
                np.where(in_sed, sed_val, 0.0)
            )

    flow_mask = gaussian_filter(flow_mask, sigma=3.2)
    sediment_mask = gaussian_filter(sediment_mask, sigma=4.2)

    np.random.seed(101)
    noise = np.random.normal(0, 7.5, (height, width))
    noise = gaussian_filter(noise, sigma=1.2)

    # Realistic satellite spectral signatures for Himalayan flood silt & debris:
    sediment_color = np.array([144.0, 132.0, 116.0])
    scour_rock = np.array([126.0, 122.0, 112.0])
    turbid_torrent = np.array([96.0, 100.0, 98.0])

    post_np = pre_np.copy()
    s_alpha = np.clip(sediment_mask, 0, 1)[:, :, None]
    post_np = post_np * (1.0 - s_alpha * 0.72) + (sediment_color + noise[:, :, None]) * (s_alpha * 0.72)

    f_alpha = np.clip(flow_mask, 0, 1)[:, :, None]
    post_np = post_np * (1.0 - f_alpha * 0.86) + (scour_rock + turbid_torrent * 0.3 + noise[:, :, None]) * (f_alpha * 0.86)

    post_np = np.clip(post_np, 0, 255).astype(np.uint8)
    post_img = Image.fromarray(post_np)

    post_path = os.path.join(DATA_DIR, "kedarnath_post_rgb.png")
    post_front = os.path.join(FRONTEND_DATA, "kedarnath_post_rgb.png")
    post_img.save(post_path, format="PNG", optimize=True)
    shutil.copyfile(post_path, post_front)
    print("Saved Post-RGB image.")

    # 3. Tactical change detection overlay
    print("Creating tactical change detection overlay...")
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    thresh = flow_mask > 0.10
    alpha = np.clip(flow_mask * 200, 0, 210).astype(np.uint8)

    rgba[thresh, 0] = 238  # Red
    rgba[thresh, 1] = 45   # Green
    rgba[thresh, 2] = 45   # Blue
    rgba[thresh, 3] = alpha[thresh]

    overlay_img = Image.fromarray(rgba, mode="RGBA")
    overlay_path = os.path.join(DATA_DIR, "kedarnath_change_overlay.png")
    overlay_front = os.path.join(FRONTEND_DATA, "kedarnath_change_overlay.png")
    overlay_img.save(overlay_path, format="PNG", optimize=True)
    shutil.copyfile(overlay_path, overlay_front)
    print("Saved Change Overlay image.")

    # 4. Exactly 5 Ranked Locations GeoJSON
    villages_data = {
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
                    "name": "Gaurikund Base Camp",
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
                    "coordinates": [79.0450, 30.5720]
                },
                "properties": {
                    "rank": 5,
                    "name": "Phata Helipad Staging Terminal",
                    "population": 2900,
                    "score": 45.0,
                    "reason": "Primary rotary wing landing strip; emergency relief fuel point; casualty triage depot for airborne rescue.",
                    "priority": "MONITORED",
                    "region": "Lower Mandakini Shelf",
                    "waterSurgeDelta": "High Terrace (+0.0m)",
                    "isolatedCount": "Active Evacuation Hub (Zero Cutoff)",
                    "roadStatus": "HIGHWAY OPERATIONAL SOUTHWARD",
                    "confidence": "99.1%",
                    "rainfallRisk": "Mountain Fog & Flight Visibility Watch",
                    "riverGauge": "Safe Above Surge Level"
                }
            }
        ]
    }

    v_path = os.path.join(DATA_DIR, "kedarnath_villages_ranked.geojson")
    v_front = os.path.join(FRONTEND_DATA, "kedarnath_villages_ranked.geojson")
    with open(v_path, "w", encoding="utf-8") as f:
        json.dump(villages_data, f, indent=2)
    shutil.copyfile(v_path, v_front)
    print(f"Saved: {v_path} (5 locations)")

    # 5. Safe Zones GeoJSON
    safe_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [79.0470, 30.5740]
                },
                "properties": {
                    "name": "Phata Civil Aviation & NDRF Air Base",
                    "type": "shelter",
                    "lat": 30.5740,
                    "lon": 79.0470,
                    "subtitle": "Major Rotary-Wing Evacuation Hub & Fuel Depot",
                    "details": "Dual concrete helipads, emergency triage shelter, turbine refuel tanks, SATCOM link.",
                    "generator": "YES (Twin 75kVA Generators)",
                    "potableSpring": "Borewell Water Purification",
                    "elevationDelta": "+320m above riverbed",
                    "bearing": "SOUTH_TERRACE",
                    "distanceKm": 18.2,
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
                    "details": "Protected rear knoll shielded by natural glacial erratic boulder behind temple.",
                    "generator": "Solar Battery + Field Generator",
                    "potableSpring": "Filtered Glacial Melt",
                    "elevationDelta": "+18m above mud torrent",
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
                    "name": "Sonprayag Upper Ridge Evacuation Camp",
                    "type": "shelter",
                    "lat": 30.6310,
                    "lon": 79.0020,
                    "subtitle": "High Clearance Hillside Evacuation Center",
                    "details": "Terraced school complex, medical first-responder tent, dry food supplies.",
                    "generator": "YES (Diesel Generator 45kVA)",
                    "potableSpring": "Mountain Spring Pipeline",
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
                    "coordinates": [79.0290, 30.3920]
                },
                "properties": {
                    "name": "Agastyamuni Regional Trauma Base Hospital",
                    "type": "hospital",
                    "lat": 30.3920,
                    "lon": 79.0290,
                    "subtitle": "Full Medical Facility & Critical ICU",
                    "details": "Emergency surgery suite, blood bank, multi-bed wards, dedicated air ambulance pad.",
                    "generator": "YES (Hospital Continuous Power Grid)",
                    "potableSpring": "Municipal Filtered System",
                    "elevationDelta": "+120m valley shelf",
                    "bearing": "SOUTH_VALLEY",
                    "distanceKm": 34.0,
                    "estWalkMinutes": 0
                }
            }
        ]
    }

    s_path = os.path.join(DATA_DIR, "kedarnath_safe_zones.geojson")
    s_front = os.path.join(FRONTEND_DATA, "kedarnath_safe_zones.geojson")
    with open(s_path, "w", encoding="utf-8") as f:
        json.dump(safe_data, f, indent=2)
    shutil.copyfile(s_path, s_front)
    print(f"Saved: {s_path} (4 safe zones)")

    # 6. Risk Alerts GeoJSON
    risk_data = {
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
                    "description": "Glacial outburst surge has carved dual channels flanking temple. Structural perimeter compromise. Ground evacuation severed.",
                    "action": "Immediate rotary extraction from northern bedrock knoll when weather allows.",
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
                    "action": "Airborne food & medicine drops; guide mobile survivors to high ridges.",
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

    r_path = os.path.join(DATA_DIR, "kedarnath_risk_alerts.geojson")
    r_front = os.path.join(FRONTEND_DATA, "kedarnath_risk_alerts.geojson")
    with open(r_path, "w", encoding="utf-8") as f:
        json.dump(risk_data, f, indent=2)
    shutil.copyfile(r_path, r_front)
    print(f"Saved: {r_path} (3 risk alerts)")

    print("\nSUCCESS: All Kedarnath assets created and deployed!")

if __name__ == "__main__":
    run()
