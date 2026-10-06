#!/usr/bin/env python3
"""
rank_villages.py - Prioritize disaster-affected villages based on satellite change masks,
population estimates, road blockage severity, hospital accessibility, and model confidence.

Run from repository root:
    python scripts/rank_villages.py
    python scripts/rank_villages.py --small
"""

import argparse
import json
import os
import sys
import time
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.mask import mask as rasterio_mask
from rasterio.transform import rowcol
from rasterio.warp import reproject, Resampling
import requests
from shapely.geometry import Point, LineString, Polygon, mapping
from shapely.ops import unary_union

warnings.filterwarnings("ignore")

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


# =============================================================================
# NAMED CONSTANTS & CONFIGURATION
# =============================================================================

# Primary confidence raster filename (switchable here; checked first, falls back to fallback if absent)
CONFIDENCE_RASTER_FILE = "ml_probability.tif"
FALLBACK_CONFIDENCE_RASTER_FILE = "confidence.tif"

POPULATION_BY_PLACE = {
    "town": 5000,
    "village": 400,
    "hamlet": 100,
    "other": 200,
}

WEIGHT_BLOCKED_ROAD = 0.30
WEIGHT_HOSPITAL_DISTANCE = 0.20
HOSPITAL_MAX_DIST_KM = 30.0

VILLAGE_BUFFER_M = 1000.0        # 1 km circle in UTM for village area
ROAD_BUFFER_M = 2000.0           # 2 km radius for road sampling
ROAD_SAMPLE_STEP_M = 50.0        # 50 m point sampling along road segments
RIVER_DUMMY_BUFFER_M = 300.0     # 300 m buffer for dummy mask generation

IGNORED_HIGHWAYS = {
    "footway", "steps", "path", "cycleway", "pedestrian", "bridleway"
}


# =============================================================================
# HELPER & OSM DOWNLOAD/CACHE FUNCTIONS
# =============================================================================

def _log(msg: str) -> None:
    try:
        print(f"[rank_villages] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[rank_villages] {msg.encode('ascii', errors='replace').decode('ascii')}", flush=True)


def download_and_cache_osm(site_name: str, mode: str, bbox: tuple, data_dir: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Download OSM layers via Overpass API mirrors and save to data/osm_cache/ as GPKG."""
    cache_dir = data_dir / "osm_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    west, south, east, north = bbox
    if mode == "small":
        mid_x = (west + east) / 2.0
        mid_y = (south + north) / 2.0
        west, south, east, north = mid_x - 0.10, mid_y - 0.10, mid_x + 0.10, mid_y + 0.10

    _log(f"Fetching OSM data for bounding box ({west:.2f}, {south:.2f}, {east:.2f}, {north:.2f})...")

    query = (
        f"[out:json][timeout:60];\n"
        f"(\n"
        f"  node[\"place\"~\"village|hamlet|town|suburb|isolated_dwelling\"]({south},{west},{north},{east});\n"
        f"  way[\"highway\"~\"primary|secondary|tertiary|trunk|motorway|residential|unclassified|service|track\"]({south},{west},{north},{east});\n"
        f"  node[\"amenity\"~\"hospital|clinic|doctors\"]({south},{west},{north},{east});\n"
        f"  way[\"amenity\"~\"hospital|clinic|doctors\"]({south},{west},{north},{east});\n"
        f"  way[\"waterway\"~\"river|stream|canal\"]({south},{west},{north},{east});\n"
        f"  relation[\"waterway\"~\"river|stream|canal\"]({south},{west},{north},{east});\n"
        f");\n"
        f"out body geom;\n"
    )

    headers = {"User-Agent": "DisasterIntelligenceRelief/1.0 (contact@emergency-response.org)"}
    servers = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]

    elements = []
    for s in servers:
        try:
            _log(f"  Attempting OSM fetch via {s} ...")
            resp = requests.post(s, data={"data": query}, headers=headers, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("elements", [])
                if len(elements) > 0:
                    _log(f"  -> Successfully retrieved {len(elements)} OSM elements from {s}")
                    break
        except Exception as e:
            _log(f"  [WARN] Server {s} failed: {e}")
            time.sleep(1)

    villages_list, roads_list, hospitals_list, rivers_list = [], [], [], []

    for el in elements:
        tags = el.get("tags", {})
        el_type = el.get("type")
        name = tags.get("name") or tags.get("name:en") or tags.get("official_name") or "Unnamed settlement"
        geom = None

        if el_type == "node":
            lat, lon = el.get("lat"), el.get("lon")
            if lat is not None and lon is not None:
                geom = Point(lon, lat)
        elif el_type in ("way", "relation") and "geometry" in el:
            pts = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(pts) >= 2:
                if pts[0] == pts[-1] and len(pts) >= 4 and "amenity" in tags:
                    geom = Polygon(pts)
                else:
                    geom = LineString(pts)

        if geom is None:
            continue

        if "place" in tags and tags["place"] in ("village", "hamlet", "town", "suburb", "isolated_dwelling"):
            villages_list.append({"name": str(name).strip(), "place": tags["place"], "geometry": geom if isinstance(geom, Point) else geom.centroid})
        elif "highway" in tags and isinstance(geom, LineString):
            roads_list.append({"name": str(name).strip(), "highway": tags["highway"], "geometry": geom})
        elif tags.get("amenity") in ("hospital", "clinic", "doctors"):
            hospitals_list.append({"name": str(name).strip(), "amenity": tags["amenity"], "geometry": geom if isinstance(geom, Point) else geom.centroid})
        elif "waterway" in tags and isinstance(geom, LineString):
            rivers_list.append({"name": str(name).strip(), "waterway": tags["waterway"], "geometry": geom})

    def to_gdf(recs):
        return gpd.GeoDataFrame(recs, crs="EPSG:4326") if recs else gpd.GeoDataFrame({"name": [], "geometry": []}, crs="EPSG:4326")

    v_gdf = to_gdf(villages_list)
    r_gdf = to_gdf(roads_list)
    h_gdf = to_gdf(hospitals_list)
    riv_gdf = to_gdf(rivers_list)

    # Save to GPKG cache
    v_gdf.to_file(cache_dir / f"{site_name}_{mode}_villages.gpkg", driver="GPKG")
    r_gdf.to_file(cache_dir / f"{site_name}_{mode}_roads.gpkg", driver="GPKG")
    h_gdf.to_file(cache_dir / f"{site_name}_{mode}_hospitals.gpkg", driver="GPKG")
    riv_gdf.to_file(cache_dir / f"{site_name}_{mode}_rivers.gpkg", driver="GPKG")

    _log(f"  -> Saved layers to cache in {cache_dir}: {len(v_gdf)} villages, {len(r_gdf)} roads, {len(h_gdf)} hospitals, {len(riv_gdf)} rivers")
    return v_gdf, r_gdf, h_gdf, riv_gdf


def load_cached_osm_layers(site_name: str, mode: str, bbox: tuple, data_dir: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Load cached GPKG files created by safe_zones.py or download if missing or empty.
    """
    cache_dir = data_dir / "osm_cache"
    layer_names = ["villages", "roads", "hospitals", "rivers"]
    all_exist = all((cache_dir / f"{site_name}_{mode}_{layer}.gpkg").exists() for layer in layer_names)

    if all_exist:
        try:
            v_test = gpd.read_file(cache_dir / f"{site_name}_{mode}_villages.gpkg")
            if len(v_test) > 0:
                gdfs = {}
                for layer in layer_names:
                    filename = f"{site_name}_{mode}_{layer}.gpkg"
                    filepath = cache_dir / filename
                    gdf = gpd.read_file(filepath)
                    gdfs[layer] = gdf
                    _log(f"  Loaded {len(gdf)} features from {filename}")
                return gdfs["villages"], gdfs["roads"], gdfs["hospitals"], gdfs["rivers"]
        except Exception:
            pass

    _log(f"OSM cache missing or empty in {cache_dir}. Populating cache files...")
    return download_and_cache_osm(site_name, mode, bbox, data_dir)


def get_change_mask_dataset(data_dir: Path, rivers_gdf: gpd.GeoDataFrame, utm_epsg: str) -> tuple[np.ndarray, rasterio.Affine, str, tuple[int, int]]:
    """
    Returns (mask_array, transform, crs, srtm_shape).
    If data/change_mask.tif exists:
      - Uses REAL change mask.
      - If change_mask.tif and srtm grid have different CRS or shape, resamples in-memory
        to match the SRTM grid using nearest-neighbour resampling without modifying any .tif.
    Otherwise:
      - Creates data/dummy_change_mask.tif on the grid of srtm.tif by rasterizing 300m buffered rivers,
        and prints a loud warning.
    """
    real_mask_fname = SITE.get("change_mask_file", "change_mask.tif" if SITE.get("name") == "sikkim" else f"{SITE.get('name')}_change_mask.tif")
    real_mask_path = data_dir / real_mask_fname
    dummy_mask_path = data_dir / f"{SITE.get('name')}_dummy_change_mask.tif"
    dem_filename = SITE.get("dem_file", f"{SITE.get('name')}_srtm.tif")
    srtm_path = data_dir / dem_filename

    # Read base SRTM grid specs
    if not srtm_path.exists():
        _log(f"ERROR: Base DEM raster not found at {srtm_path}")
        sys.exit(1)

    with rasterio.open(srtm_path) as srtm_src:
        srtm_transform = srtm_src.transform
        srtm_crs = srtm_src.crs
        srtm_shape = srtm_src.shape

    if real_mask_path.exists():
        _log(f"Using REAL change mask from {real_mask_path}")
        with rasterio.open(real_mask_path) as mask_src:
            mask_data = mask_src.read(1)
            mask_transform = mask_src.transform
            mask_crs = mask_src.crs
            mask_shape = mask_src.shape

            # Check if resampling in memory is needed to match SRTM grid
            if mask_shape != srtm_shape or mask_crs != srtm_crs or mask_transform != srtm_transform:
                _log(f"  In-memory resampling change mask from shape {mask_shape} to SRTM shape {srtm_shape} (Nearest Neighbour)...")
                resampled_mask = np.zeros(srtm_shape, dtype=np.uint8)
                reproject(
                    source=mask_data,
                    destination=resampled_mask,
                    src_transform=mask_transform,
                    src_crs=mask_crs,
                    dst_transform=srtm_transform,
                    dst_crs=srtm_crs,
                    resampling=Resampling.nearest,
                )
                final_mask = (resampled_mask == 1)
            else:
                final_mask = (mask_data == 1)

            changed_count = np.count_nonzero(final_mask)
            _log(f"  -> REAL change mask loaded: {changed_count:,} changed pixels ({changed_count/final_mask.size*100:.2f}%)")
            return final_mask, srtm_transform, srtm_crs, srtm_shape

    # DUMMY MASK PATH (only when change_mask.tif is absent)
    print("\n" + "=" * 70, flush=True)
    print("  WARNING: DUMMY MASK in use, not a real result", flush=True)
    print("=" * 70 + "\n", flush=True)

    _log(f"Creating dummy change mask on SRTM grid ({srtm_shape[0]}x{srtm_shape[1]})...")

    if not rivers_gdf.empty:
        rivers_utm = rivers_gdf.to_crs(utm_epsg)
        buffered_rivers_utm = rivers_utm.buffer(RIVER_DUMMY_BUFFER_M)
        buffered_rivers_wgs84 = buffered_rivers_utm.to_crs(srtm_crs)
        combined_geom = unary_union(buffered_rivers_wgs84.geometry)
        geoms_to_rasterize = [mapping(combined_geom)] if not combined_geom.is_empty else []
    else:
        line = LineString([(88.55, 27.75), (88.53, 27.50), (88.48, 27.30), (88.40, 27.15)])
        line_utm = gpd.GeoSeries([line], crs="EPSG:4326").to_crs(utm_epsg).buffer(300.0).to_crs(srtm_crs).iloc[0]
        geoms_to_rasterize = [mapping(line_utm)]

    if geoms_to_rasterize:
        dummy_mask = rasterize(
            shapes=((g, 1) for g in geoms_to_rasterize),
            out_shape=srtm_shape,
            transform=srtm_transform,
            fill=0,
            dtype=np.uint8,
        )
    else:
        dummy_mask = np.zeros(srtm_shape, dtype=np.uint8)

    with rasterio.open(srtm_path) as srtm_src:
        profile = srtm_src.profile.copy()
    profile.update(dtype=rasterio.uint8, count=1, nodata=0)
    with rasterio.open(dummy_mask_path, "w", **profile) as dst:
        dst.write(dummy_mask, 1)
    _log(f"  -> Saved {dummy_mask_path}")

    return (dummy_mask == 1), srtm_transform, srtm_crs, srtm_shape


def get_confidence_raster_dataset(data_dir: Path, target_shape: tuple[int, int], target_transform: rasterio.Affine, target_crs: str) -> tuple[np.ndarray | None, str | None]:
    """
    Load confidence/probability raster.
    Checks CONFIDENCE_RASTER_FILE (e.g. ml_probability.tif), falls back to FALLBACK_CONFIDENCE_RASTER_FILE (confidence.tif).
    If neither exists, returns (None, None) and logs a warning.
    Resamples in-memory to match the target grid if dimensions/CRS differ.
    """
    primary_path = data_dir / CONFIDENCE_RASTER_FILE
    fallback_path = data_dir / FALLBACK_CONFIDENCE_RASTER_FILE

    chosen_path = None
    if primary_path.exists():
        chosen_path = primary_path
        _log(f"Using primary confidence raster from {chosen_path.name}")
    elif fallback_path.exists():
        chosen_path = fallback_path
        _log(f"Primary confidence raster '{CONFIDENCE_RASTER_FILE}' not found. Using fallback confidence raster '{chosen_path.name}'")
    else:
        print("\n" + "=" * 70, flush=True)
        print(f"  WARNING: Neither '{CONFIDENCE_RASTER_FILE}' nor '{FALLBACK_CONFIDENCE_RASTER_FILE}' exists.", flush=True)
        print("  Confidence column will be empty.", flush=True)
        print("=" * 70 + "\n", flush=True)
        return None, None

    with rasterio.open(chosen_path) as src:
        conf_data = src.read(1).astype(np.float32)
        conf_transform = src.transform
        conf_crs = src.crs
        conf_shape = src.shape

    # In-memory resampling if grid differs
    if conf_shape != target_shape or conf_crs != target_crs or conf_transform != target_transform:
        _log(f"  In-memory resampling confidence raster from shape {conf_shape} to grid shape {target_shape} (Bilinear)...")
        resampled_conf = np.zeros(target_shape, dtype=np.float32)
        reproject(
            source=conf_data,
            destination=resampled_conf,
            src_transform=conf_transform,
            src_crs=conf_crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.bilinear,
        )
        return resampled_conf, chosen_path.name

    return conf_data, chosen_path.name


def sample_mask_at_point(x_coord: float, y_coord: float, mask: np.ndarray, transform: rasterio.Affine) -> int:
    """Sample binary mask at given (x, y) coordinates."""
    try:
        r, c = rowcol(transform, x_coord, y_coord)
        if 0 <= r < mask.shape[0] and 0 <= c < mask.shape[1]:
            return 1 if mask[r, c] else 0
    except Exception:
        pass
    return 0


def compute_polygon_mask_fraction(polygon_wgs84: Polygon, mask: np.ndarray, transform: rasterio.Affine) -> float:
    """Compute fraction of pixels inside polygon that equal True in mask."""
    try:
        minx, miny, maxx, maxy = polygon_wgs84.bounds
        r_min, c_min = rowcol(transform, minx, maxy)
        r_max, c_max = rowcol(transform, maxx, miny)

        r_start = max(0, min(r_min, r_max))
        r_end = min(mask.shape[0], max(r_min, r_max) + 1)
        c_start = max(0, min(c_min, c_max))
        c_end = min(mask.shape[1], max(c_min, c_max) + 1)

        if r_start >= r_end or c_start >= c_end:
            return 0.0

        sub_mask = mask[r_start:r_end, c_start:c_end]
        sub_transform = rasterio.windows.transform(
            rasterio.windows.Window(c_start, r_start, c_end - c_start, r_end - r_start),
            transform
        )

        poly_raster = rasterize(
            shapes=[(mapping(polygon_wgs84), 1)],
            out_shape=sub_mask.shape,
            transform=sub_transform,
            fill=0,
            dtype=np.uint8,
        )

        inside_pixels = (poly_raster == 1)
        total_inside = np.count_nonzero(inside_pixels)
        if total_inside == 0:
            return 0.0

        changed_inside = np.count_nonzero(inside_pixels & sub_mask)
        return float(changed_inside / total_inside)
    except Exception:
        return 0.0


def compute_polygon_confidence(polygon_wgs84: Polygon, mask: np.ndarray, conf_raster: np.ndarray | None, transform: rasterio.Affine) -> float | None:
    """
    Compute mean confidence over village circle:
    - Only over pixels where change mask == 1.
    - If none, use the mean over the whole circle.
    - Round to 2 decimals.
    """
    if conf_raster is None:
        return None

    try:
        minx, miny, maxx, maxy = polygon_wgs84.bounds
        r_min, c_min = rowcol(transform, minx, maxy)
        r_max, c_max = rowcol(transform, maxx, miny)

        r_start = max(0, min(r_min, r_max))
        r_end = min(conf_raster.shape[0], max(r_min, r_max) + 1)
        c_start = max(0, min(c_min, c_max))
        c_end = min(conf_raster.shape[1], max(c_min, c_max) + 1)

        if r_start >= r_end or c_start >= c_end:
            return None

        sub_mask = mask[r_start:r_end, c_start:c_end]
        sub_conf = conf_raster[r_start:r_end, c_start:c_end]
        sub_transform = rasterio.windows.transform(
            rasterio.windows.Window(c_start, r_start, c_end - c_start, r_end - r_start),
            transform
        )

        poly_raster = rasterize(
            shapes=[(mapping(polygon_wgs84), 1)],
            out_shape=sub_mask.shape,
            transform=sub_transform,
            fill=0,
            dtype=np.uint8,
        )

        inside_pixels = (poly_raster == 1)
        changed_inside = inside_pixels & sub_mask

        if np.count_nonzero(changed_inside) > 0:
            val = float(np.nanmean(sub_conf[changed_inside]))
        elif np.count_nonzero(inside_pixels) > 0:
            val = float(np.nanmean(sub_conf[inside_pixels]))
        else:
            return None

        return round(val, 2)
    except Exception:
        return None


# =============================================================================
# MAIN RANKING PIPELINE
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Rank disaster-affected villages.")
    parser.add_argument("--small", action="store_true", help="Use small area test cache")
    args = parser.parse_args()

    mode = "small" if args.small else "full"
    site_name = SITE.get("name", "sikkim")
    bbox = SITE.get("bbox", (88.30, 27.15, 88.75, 27.75))
    utm_epsg = SITE.get("utm_epsg", "EPSG:32645")
    data_dir = Path(SITE.get("data_dir", ROOT_DIR / "data"))
    frontend_dir = Path(SITE.get("frontend_dir", ROOT_DIR / "frontend" / "public" / "data"))

    _log(f"Starting village ranking for site '{site_name}' (mode: {mode})...")

    # 1. Load cached OSM layers
    villages_raw, roads_raw, hospitals_raw, rivers_raw = load_cached_osm_layers(site_name, mode, bbox, data_dir)

    # Filter villages for village, hamlet, town
    if "place" in villages_raw.columns:
        valid_places = {"village", "hamlet", "town"}
        villages = villages_raw[villages_raw["place"].isin(valid_places)].copy()
    else:
        villages = villages_raw.copy()

    if villages.empty:
        _log("ERROR: No valid village points found.")
        sys.exit(1)

    _log(f"Processing {len(villages)} village / hamlet / town settlements...")

    # 2. Get change mask (in-memory resampled to SRTM grid if shapes differ)
    mask, mask_transform, mask_crs, srtm_shape = get_change_mask_dataset(data_dir, rivers_raw, utm_epsg)

    # 3. Load Confidence / ML Probability Raster
    conf_raster, conf_file_used = get_confidence_raster_dataset(data_dir, srtm_shape, mask_transform, mask_crs)

    # 4. Prepare geometric layers in UTM & WGS84
    villages_utm = villages.to_crs(utm_epsg)
    
    # Filter roads: ignore footway, steps, path, cycleway, pedestrian, bridleway
    if "highway" in roads_raw.columns:
        roads_filtered = roads_raw[~roads_raw["highway"].isin(IGNORED_HIGHWAYS)].copy()
    else:
        roads_filtered = roads_raw.copy()

    roads_utm = roads_filtered.to_crs(utm_epsg) if not roads_filtered.empty else gpd.GeoDataFrame(geometry=[], crs=utm_epsg)
    hospitals_utm = hospitals_raw.to_crs(utm_epsg) if not hospitals_raw.empty else gpd.GeoDataFrame(geometry=[], crs=utm_epsg)

    # Identify hospitals NOT inside the mask (unaffected hospitals)
    unaffected_hospitals_utm = []
    if not hospitals_raw.empty:
        hospitals_wgs84 = hospitals_raw.to_crs(mask_crs)
        for idx, hosp in hospitals_wgs84.iterrows():
            geom = hosp.geometry
            pt = geom.centroid if geom.geom_type != "Point" else geom
            if sample_mask_at_point(pt.x, pt.y, mask, mask_transform) == 0:
                unaffected_hospitals_utm.append(hospitals_utm.loc[idx].geometry.centroid)

    _log(f"  Identified {len(unaffected_hospitals_utm)} unaffected hospitals out of {len(hospitals_raw)} mapped.")

    # 5. Compute metrics per village
    ranked_records = []

    for idx, v_row in villages.iterrows():
        v_pt_utm = villages_utm.loc[idx].geometry
        if v_pt_utm.geom_type != "Point":
            v_pt_utm = v_pt_utm.centroid

        v_pt_wgs84 = v_row.geometry
        if v_pt_wgs84.geom_type != "Point":
            v_pt_wgs84 = v_pt_wgs84.centroid

        # A. Population by place type
        place_type = str(v_row.get("place", "other")).lower()
        population = POPULATION_BY_PLACE.get(place_type, POPULATION_BY_PLACE["other"])

        # B. Village area (1 km circle in UTM) & Affected fraction
        circle_utm = v_pt_utm.buffer(VILLAGE_BUFFER_M)
        circle_wgs84 = gpd.GeoSeries([circle_utm], crs=utm_epsg).to_crs(mask_crs).iloc[0]
        affected_fraction = compute_polygon_mask_fraction(circle_wgs84, mask, mask_transform)

        # C. Confidence calculation over 1 km circle
        confidence_val = compute_polygon_confidence(circle_wgs84, mask, conf_raster, mask_transform)

        # D. Blocked-road share (sampled every 50m along roads within 2 km in UTM)
        road_search_circle = v_pt_utm.buffer(ROAD_BUFFER_M)
        if not roads_utm.empty:
            nearby_roads = roads_utm[roads_utm.intersects(road_search_circle)]
        else:
            nearby_roads = gpd.GeoDataFrame(geometry=[], crs=utm_epsg)

        blocked_count = 0
        total_road_samples = 0

        for _, road in nearby_roads.iterrows():
            geom = road.geometry.intersection(road_search_circle)
            if geom.is_empty:
                continue
            
            geoms = [geom] if geom.geom_type == "LineString" else [g for g in getattr(geom, "geoms", []) if g.geom_type == "LineString"]

            for line in geoms:
                length = line.length
                if length <= 0:
                    continue
                num_steps = max(1, int(np.ceil(length / ROAD_SAMPLE_STEP_M)))
                for dist in np.linspace(0, length, num_steps):
                    sample_pt_utm = line.interpolate(dist)
                    sample_pt_wgs84 = gpd.GeoSeries([sample_pt_utm], crs=utm_epsg).to_crs(mask_crs).iloc[0]
                    total_road_samples += 1
                    if sample_mask_at_point(sample_pt_wgs84.x, sample_pt_wgs84.y, mask, mask_transform) == 1:
                        blocked_count += 1

        if total_road_samples > 0:
            blocked_road_share = float(blocked_count / total_road_samples)
        else:
            blocked_road_share = 0.0

        # E. Hospital distance to nearest unaffected hospital
        if unaffected_hospitals_utm:
            min_hosp_dist_m = min(v_pt_utm.distance(h_pt) for h_pt in unaffected_hospitals_utm)
            hosp_dist_km = min_hosp_dist_m / 1000.0
            hosp_str = f"nearest unaffected hospital {int(round(hosp_dist_km))} km away"
        else:
            hosp_dist_km = HOSPITAL_MAX_DIST_KM
            hosp_str = "no unaffected hospital mapped"

        # F. Composite Score
        hosp_penalty_factor = min(hosp_dist_km / HOSPITAL_MAX_DIST_KM, 1.0)

        if affected_fraction > 0 or blocked_road_share > 0:
            score = (
                (population * affected_fraction) +
                (WEIGHT_BLOCKED_ROAD * population * blocked_road_share) +
                (WEIGHT_HOSPITAL_DISTANCE * population * hosp_penalty_factor)
            )
        else:
            score = 0.0

        score = float(np.round(score, 2))

        # G. Plain-language reason string
        if blocked_road_share >= 0.5:
            road_phrase = "access roads mostly blocked"
        elif blocked_road_share > 0:
            road_phrase = "some access road blocked"
        else:
            road_phrase = "access roads clear"

        affected_pct = int(round(affected_fraction * 100))
        reason = f"~{population} people (est.), {affected_pct}% of area changed, {road_phrase}, {hosp_str}"

        # Resolve settlement name
        name = v_row.get("name")
        if not name or str(name).strip() in ("", "None", "nan", "Unnamed"):
            name = "Unnamed settlement"
        else:
            name = str(name).strip()

        ranked_records.append({
            "name": name,
            "population": int(population),
            "score": score,
            "reason": reason,
            "confidence": confidence_val,
            "geometry": v_pt_wgs84,
        })

    # 6. Filter: keep only villages with score > 0
    gdf_all = gpd.GeoDataFrame(ranked_records, crs="EPSG:4326")
    gdf_positive = gdf_all[gdf_all["score"] > 0.0].copy()

    # Sort descending by score
    gdf_sorted = gdf_positive.sort_values(by="score", ascending=False).reset_index(drop=True)
    gdf_sorted["rank"] = gdf_sorted.index + 1

    # Keep exact required properties: rank, name, population, score, reason, confidence
    output_gdf = gdf_sorted[["rank", "name", "population", "score", "reason", "confidence", "geometry"]].copy()

    # 7. Save GeoJSON outputs
    data_dir.mkdir(parents=True, exist_ok=True)
    villages_fname = SITE.get("villages_ranked_file", "villages_ranked.geojson" if site_name == "sikkim" else f"{site_name}_villages_ranked.geojson")
    out_file_data = data_dir / villages_fname
    output_gdf.to_file(out_file_data, driver="GeoJSON")
    _log(f"Saved {len(output_gdf)} ranked villages -> {out_file_data}")

    try:
        frontend_dir.mkdir(parents=True, exist_ok=True)
        out_file_frontend = frontend_dir / villages_fname
        output_gdf.to_file(out_file_frontend, driver="GeoJSON")
        _log(f"Saved {len(output_gdf)} ranked villages -> {out_file_frontend}")
    except Exception as e:
        _log(f"  [WARN] Could not copy to frontend dir: {e}")

    # Compute min and max score
    min_score = float(output_gdf["score"].min()) if len(output_gdf) > 0 else 0.0
    max_score = float(output_gdf["score"].max()) if len(output_gdf) > 0 else 0.0

    # 8. Print top 10 rows and summary statistics
    print("\n" + "=" * 110, flush=True)
    print(f"  TOP 10 RANKED VILLAGES (Total with Score > 0: {len(output_gdf)} / {len(gdf_all)})", flush=True)
    print(f"  Score Range: Min = {min_score:.2f}, Max = {max_score:.2f} | Confidence Raster Used: {conf_file_used}", flush=True)
    print("=" * 110, flush=True)
    print(f"{'Rank':<6} {'Name':<22} {'Pop':<7} {'Score':<9} {'Conf':<7} {'Reason'}", flush=True)
    print("-" * 110, flush=True)
    for _, row in output_gdf.head(10).iterrows():
        conf_str = f"{row['confidence']:.2f}" if row['confidence'] is not None and not np.isnan(row['confidence']) else "N/A"
        print(f"#{row['rank']:<5} {row['name'][:20]:<22} {row['population']:<7} {row['score']:<9.2f} {conf_str:<7} {row['reason']}", flush=True)
    print("=" * 110 + "\n", flush=True)


if __name__ == "__main__":
    main()
