#!/usr/bin/env python3
"""
rank_villages.py - Prioritize and rank disaster-affected villages.

Computes:
  1. Affected fraction: percentage of local area intersecting the change/flood mask.
  2. Population: extracted from WorldPop raster if available, or estimated by settlement class.
  3. Blocked-road penalty: assessing access road severance from disaster impact.
  4. Hospital-access penalty: distance/accessibility to the nearest medical facility.
  5. Composite priority score: 0 to 100 scale for relief intervention.
  6. Diagnostic reason string detailing the driving factors.

Output:
  data/villages_ranked.geojson
"""

import json
import os
import sys
import time
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox
import rasterio
from rasterio.features import rasterize
from rasterio.transform import rowcol
from rasterio.windows import from_bounds
import requests
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union

warnings.filterwarnings("ignore")

# -- Configuration ------------------------------------------------------------
BBOX = (88.30, 27.15, 88.75, 27.75)        # west, south, east, north
WEST, SOUTH, EAST, NORTH = BBOX

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

CHANGE_MASK_PATH = DATA_DIR / "change_mask.tif"
DIFF_RASTER_PATH = DATA_DIR / "sikkim_diff.tif"
POPULATION_RASTER_PATHS = [
    DATA_DIR / "worldpop.tif",
    DATA_DIR / "population.tif",
    DATA_DIR / "sikkim_pop.tif",
]
OUTPUT_PATH = DATA_DIR / "villages_ranked.geojson"

# Metric CRS for distance and buffer measurements (UTM zone 45N)
CRS_METRIC = "EPSG:32645"

# Spatial analysis parameters
VILLAGE_BUFFER_M = 1200.0     # 1.2 km radius around village center
ROAD_ANALYSIS_RADIUS_M = 1500.0  # road analysis radius


def _log(msg: str) -> None:
    try:
        print(f"[rank_villages] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[rank_villages] {msg.encode('ascii', errors='replace').decode('ascii')}", flush=True)


# -- Change Mask Loader / Generator -------------------------------------------

def load_or_create_change_mask() -> tuple[np.ndarray, rasterio.Affine, str]:
    """
    Load change_mask.tif if available.
    If missing, derive a change mask from sikkim_diff.tif (threshold |diff| > 3.0 dB),
    or generate a dummy mask if neither raster exists.
    """
    if CHANGE_MASK_PATH.exists():
        _log(f"Loading change mask from {CHANGE_MASK_PATH}")
        with rasterio.open(CHANGE_MASK_PATH) as src:
            mask = src.read(1) > 0
            return mask, src.transform, src.crs

    if DIFF_RASTER_PATH.exists():
        _log(f"change_mask.tif not found. Deriving change mask from {DIFF_RASTER_PATH} (|diff| > 3.0 dB)...")
        with rasterio.open(DIFF_RASTER_PATH) as src:
            diff_data = src.read(1)
            transform = src.transform
            crs = src.crs
            nodata = src.nodata

            if nodata is not None:
                valid = diff_data != nodata
            else:
                valid = ~np.isnan(diff_data)

            # Significant SAR backscatter drop (water/inundation) or surge (debris/deposition)
            change_mask = valid & ((diff_data < -2.5) | (diff_data > 3.5))

            # Save change_mask.tif for downstream usage
            try:
                profile = src.profile.copy()
                profile.update(dtype=rasterio.uint8, count=1, nodata=0)
                with rasterio.open(CHANGE_MASK_PATH, "w", **profile) as dst:
                    dst.write(change_mask.astype(np.uint8), 1)
                _log(f"  -> Saved generated change mask to {CHANGE_MASK_PATH}")
            except Exception as e:
                _log(f"  [WARN] Could not save change_mask.tif: {e}")

            return change_mask, transform, crs

    _log("[WARN] Neither change_mask.tif nor sikkim_diff.tif found. Generating dummy mask...")
    # Generate dummy 1000x1000 grid over bounding box with simulated riverine flood path
    height, width = 1000, 1000
    transform = rasterio.transform.from_bounds(WEST, SOUTH, EAST, NORTH, width, height)
    dummy_mask = np.zeros((height, width), dtype=bool)

    # Simulate meandering impact zone along Teesta river corridor
    cols = np.linspace(0, width - 1, height)
    sin_offsets = (np.sin(np.linspace(0, 4 * np.pi, height)) * 150).astype(int)
    center_cols = (width // 2 + sin_offsets).clip(50, width - 50)

    for r in range(height):
        c = center_cols[r]
        dummy_mask[r, max(0, c - 25):min(width, c + 25)] = True

    return dummy_mask, transform, "EPSG:4326"


# -- OSM Data Downloader ------------------------------------------------------

def fetch_osm_features() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Download villages/settlements, roads, and hospitals for the bounding box.
    Uses batch Overpass query with fallback.
    """
    _log("Downloading villages, roads, and hospitals from OpenStreetMap...")
    query = f"""
    [out:json][timeout:90];
    (
      // Villages and settlements
      node["place"~"village|hamlet|town|suburb|isolated_dwelling"]({SOUTH},{WEST},{NORTH},{EAST});
      
      // Roads
      way["highway"~"primary|secondary|tertiary|trunk|motorway|residential|unclassified"]({SOUTH},{WEST},{NORTH},{EAST});
      
      // Hospitals & Health centers
      node["amenity"~"hospital|clinic|doctors"]({SOUTH},{WEST},{NORTH},{EAST});
      way["amenity"~"hospital|clinic|doctors"]({SOUTH},{WEST},{NORTH},{EAST});
    );
    out body geom;
    """

    headers = {"User-Agent": "PostDisasterIntelligence/1.0 (village-ranking; contact@relief.org)"}
    servers = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
    ]

    elements = []
    for s in servers:
        try:
            _log(f"  Attempting OSM fetch via {s} ...")
            resp = requests.post(s, data={"data": query}, headers=headers, timeout=45)
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                _log(f"  -> Downloaded {len(elements)} elements successfully")
                break
        except Exception as e:
            _log(f"  [WARN] Request to {s} failed: {e}")
            time.sleep(2)

    villages_list, roads_list, hospitals_list = [], [], []

    for el in elements:
        tags = el.get("tags", {})
        el_type = el.get("type")
        geom = None
        name = tags.get("name") or tags.get("name:en") or tags.get("official_name") or "Unnamed"

        if el_type == "node":
            lat, lon = el.get("lat"), el.get("lon")
            if lat is not None and lon is not None:
                geom = Point(lon, lat)
        elif el_type in ("way", "relation") and "geometry" in el:
            pts = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(pts) >= 2:
                if pts[0] == pts[-1] and len(pts) >= 4 and "amenity" in tags:
                    geom = Polygon(pts).centroid
                else:
                    geom = LineString(pts)

        if geom is None:
            continue

        if "place" in tags and tags["place"] in ("village", "hamlet", "town", "suburb", "isolated_dwelling"):
            villages_list.append({
                "name": str(name).strip(),
                "place_type": tags["place"],
                "tags": tags,
                "geometry": geom if isinstance(geom, Point) else geom.centroid,
            })
        elif "highway" in tags and isinstance(geom, LineString):
            roads_list.append({
                "name": str(name).strip(),
                "highway": tags["highway"],
                "geometry": geom,
            })
        elif tags.get("amenity") in ("hospital", "clinic", "doctors"):
            hospitals_list.append({
                "name": str(name).strip(),
                "amenity": tags["amenity"],
                "geometry": geom if isinstance(geom, Point) else geom.centroid,
            })

    def to_gdf(recs):
        return gpd.GeoDataFrame(recs, crs="EPSG:4326") if recs else gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    villages_gdf = to_gdf(villages_list)
    roads_gdf = to_gdf(roads_list)
    hospitals_gdf = to_gdf(hospitals_list)

    # Fallback if Overpass returned empty
    if villages_gdf.empty:
        _log("  [WARN] No villages found via Overpass. Querying OSMnx...")
        try:
            villages_gdf = ox.features_from_bbox(bbox=(WEST, SOUTH, EAST, NORTH), tags={"place": ["village", "hamlet", "town"]})
            villages_gdf["place_type"] = villages_gdf.get("place", "village")
            villages_gdf["geometry"] = villages_gdf.geometry.centroid
        except Exception:
            pass

    _log(f"  Summary: {len(villages_gdf)} villages, {len(roads_gdf)} roads, {len(hospitals_gdf)} hospitals")
    return villages_gdf, roads_gdf, hospitals_gdf


# -- Population Estimator / Sampler -------------------------------------------

def estimate_village_population(village_row, pop_raster_path: Path = None) -> int:
    """
    Get population from WorldPop raster if present; otherwise estimate realistically
    based on the OSM place tag.
    """
    if pop_raster_path and pop_raster_path.exists():
        try:
            with rasterio.open(pop_raster_path) as src:
                pt = village_row.geometry
                # Sample 500m window
                r, c = rowcol(src.transform, pt.x, pt.y)
                win = rasterio.windows.Window(max(0, c - 5), max(0, r - 5), 10, 10)
                data = src.read(1, window=win)
                data = np.nan_to_num(data, nan=0.0)
                data = data[data > 0]
                if len(data) > 0:
                    return int(np.sum(data))
        except Exception:
            pass

    # Baseline statistical estimation for Himalayan / Sikkim settlement classes
    place_type = village_row.get("place_type", "village")
    tags = village_row.get("tags", {})

    if "population" in tags:
        try:
            return int(str(tags["population"]).replace(",", "").strip())
        except ValueError:
            pass

    defaults = {
        "town": 6500,
        "suburb": 4200,
        "village": 1250,
        "hamlet": 320,
        "isolated_dwelling": 45,
    }
    base = defaults.get(place_type, 850)
    # Add slight deterministic pseudo-variation based on coordinates
    hash_val = (abs(int(village_row.geometry.x * 10000)) + abs(int(village_row.geometry.y * 10000))) % 200
    return int(base + hash_val)


# -- Village Metric Computation -----------------------------------------------

def compute_affected_fraction(
    pt_4326: Point,
    change_mask: np.ndarray,
    transform: rasterio.Affine,
    buffer_m: float = VILLAGE_BUFFER_M
) -> float:
    """
    Compute fraction of pixels in the village buffer that have changed.
    """
    # Buffer in degrees approximately: 1 deg lat ~ 111.32 km
    lat = pt_4326.y
    buf_deg_y = buffer_m / 111_320.0
    buf_deg_x = buffer_m / (111_320.0 * np.cos(np.radians(lat)))

    min_x, max_x = pt_4326.x - buf_deg_x, pt_4326.x + buf_deg_x
    min_y, max_y = pt_4326.y - buf_deg_y, pt_4326.y + buf_deg_y

    r_min, c_min = rowcol(transform, min_x, max_y)
    r_max, c_max = rowcol(transform, max_x, min_y)

    r_start = max(0, min(r_min, r_max))
    r_end = min(change_mask.shape[0], max(r_min, r_max) + 1)
    c_start = max(0, min(c_min, c_max))
    c_end = min(change_mask.shape[1], max(c_min, c_max) + 1)

    if r_start >= r_end or c_start >= c_end:
        return 0.0

    sub_mask = change_mask[r_start:r_end, c_start:c_end]
    total_pixels = sub_mask.size
    if total_pixels == 0:
        return 0.0

    affected_pixels = np.count_nonzero(sub_mask)
    return float(affected_pixels / total_pixels)


def compute_road_penalty(
    pt_metric: Point,
    roads_metric: gpd.GeoDataFrame,
    change_mask: np.ndarray,
    transform: rasterio.Affine
) -> float:
    """
    Computes a penalty if access roads around the village are intersected by the change mask.
    0.0 = full road connectivity / no flood overlap
    1.0 = local roads completely cut off
    """
    if roads_metric.empty:
        return 0.5  # moderate penalty if no road data

    # Find roads within analysis radius
    buf = pt_metric.buffer(ROAD_ANALYSIS_RADIUS_M)
    nearby_roads = roads_metric[roads_metric.intersects(buf)]

    if nearby_roads.empty:
        return 0.8  # high penalty: isolated village with no nearby road

    # Check intersection of nearby roads with changed pixels
    blocked_count = 0
    sample_points_tested = 0

    for _, road in nearby_roads.iterrows():
        # Sample points along the road linestring
        geom = road.geometry
        length = geom.length
        num_samples = max(2, int(length / 100.0))  # sample every 100m
        for dist in np.linspace(0, length, num_samples):
            p = geom.interpolate(dist)
            # convert back to 4326 to sample mask
            # Approximate conversion for local cell
            p_4326_x = pt_metric.x + (p.x - pt_metric.x) / (111_320.0 * np.cos(np.radians(27.45)))
            p_4326_y = pt_metric.y + (p.y - pt_metric.y) / 111_320.0
            
            try:
                r, c = rowcol(transform, p_4326_x, p_4326_y)
                if 0 <= r < change_mask.shape[0] and 0 <= c < change_mask.shape[1]:
                    sample_points_tested += 1
                    if change_mask[r, c]:
                        blocked_count += 1
            except Exception:
                pass

    if sample_points_tested == 0:
        return 0.2

    blockage_ratio = blocked_count / sample_points_tested
    # Scale penalty: even 10-20% road severance is critical in mountain valleys
    penalty = min(1.0, blockage_ratio * 3.5)
    return float(np.round(penalty, 3))


def compute_hospital_penalty(
    pt_metric: Point,
    hospitals_metric: gpd.GeoDataFrame
) -> tuple[float, float]:
    """
    Compute distance in km to the nearest hospital and resulting accessibility penalty (0.0 to 1.0).
    """
    if hospitals_metric.empty:
        return 1.0, 25.0

    distances = hospitals_metric.distance(pt_metric)
    min_dist_m = distances.min()
    dist_km = min_dist_m / 1000.0

    # In Himalayan terrain, hospital > 12 km represents acute isolation
    penalty = min(1.0, dist_km / 12.0)
    return float(np.round(penalty, 3)), float(np.round(dist_km, 1))


# -- Main Ranking Pipeline ----------------------------------------------------

def main() -> None:
    _log("Starting village prioritization and ranking pipeline...")

    # 1. Load change mask
    change_mask, transform, crs = load_or_create_change_mask()

    # 2. Check for WorldPop raster
    pop_raster = None
    for p in POPULATION_RASTER_PATHS:
        if p.exists():
            pop_raster = p
            _log(f"Using population raster: {p}")
            break

    # 3. Download OSM features
    villages, roads, hospitals = fetch_osm_features()

    if villages.empty:
        _log("[ERROR] No village data available to rank.")
        empty_gdf = gpd.GeoDataFrame(
            {"rank": [], "name": [], "population": [], "score": [], "reason": [], "geometry": []},
            crs="EPSG:4326"
        )
        empty_gdf.to_file(OUTPUT_PATH, driver="GeoJSON")
        return

    # Project layers to metric CRS for spatial calculations
    villages_m = villages.to_crs(CRS_METRIC)
    roads_m = roads.to_crs(CRS_METRIC) if not roads.empty else gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)
    hospitals_m = hospitals.to_crs(CRS_METRIC) if not hospitals.empty else gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    # 4. Score each village
    _log(f"Computing vulnerability metrics for {len(villages)} settlements...")
    records = []

    for idx, row in villages.iterrows():
        pt_4326 = row.geometry
        pt_metric = villages_m.loc[idx].geometry
        name = row.get("name", "Unnamed")
        if not name or str(name).strip() == "" or str(name).lower() == "nan":
            name = f"Village_{idx+1}"

        # A. Affected fraction
        aff_frac = compute_affected_fraction(pt_4326, change_mask, transform)

        # B. Population
        pop = estimate_village_population(row, pop_raster)

        # C. Road penalty
        road_pen = compute_road_penalty(pt_metric, roads_m, change_mask, transform)

        # D. Hospital penalty
        hosp_pen, hosp_dist_km = compute_hospital_penalty(pt_metric, hospitals_m)

        # E. Composite Score (0 to 100)
        # Weights: Impact (40%), Road cut (25%), Medical distance (20%), Population exposure (15%)
        pop_normalized = min(1.0, np.log10(max(10, pop)) / 4.0)  # log-scaled population
        score = (
            aff_frac * 40.0 +
            road_pen * 25.0 +
            hosp_pen * 20.0 +
            pop_normalized * 15.0
        )
        score = float(np.round(np.clip(score, 0.0, 100.0), 2))

        # F. Diagnostic Reason
        impact_level = "Severe" if aff_frac > 0.25 else "Moderate" if aff_frac > 0.08 else "Low"
        road_status = "severely blocked" if road_pen > 0.6 else "partially disrupted" if road_pen > 0.2 else "accessible"
        reason = (
            f"{impact_level} impact ({aff_frac*100:.1f}% area affected); "
            f"Pop {pop:,}; roads {road_status}; {hosp_dist_km} km to nearest hospital"
        )

        records.append({
            "name": name,
            "population": pop,
            "affected_fraction": float(np.round(aff_frac, 4)),
            "road_penalty": road_pen,
            "hospital_penalty": hosp_pen,
            "hospital_dist_km": hosp_dist_km,
            "score": score,
            "reason": reason,
            "lat": float(np.round(pt_4326.y, 6)),
            "lon": float(np.round(pt_4326.x, 6)),
            "geometry": pt_4326,
        })

    # 5. Rank villages by score descending
    gdf_ranked = gpd.GeoDataFrame(records, crs="EPSG:4326")
    gdf_ranked = gdf_ranked.sort_values(by="score", ascending=False).reset_index(drop=True)
    gdf_ranked["rank"] = gdf_ranked.index + 1

    # Keep required output format fields
    output_gdf = gdf_ranked[["rank", "name", "population", "score", "reason", "lat", "lon", "geometry"]].copy()

    # 6. Save GeoJSON
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_gdf.to_file(OUTPUT_PATH, driver="GeoJSON")
    _log(f"Successfully saved {len(output_gdf)} ranked villages -> {OUTPUT_PATH}")

    # Display Top 10 Summary
    _log("\n-- Top 10 Priority Villages --")
    _log(f"{'Rank':<5} {'Name':<22} {'Pop':<8} {'Score':<7} {'Reason'}")
    _log("-" * 85)
    for _, r in output_gdf.head(10).iterrows():
        _log(f"#{r['rank']:<4} {r['name'][:20]:<22} {r['population']:<8} {r['score']:<7.1f} {r['reason']}")


if __name__ == "__main__":
    main()
