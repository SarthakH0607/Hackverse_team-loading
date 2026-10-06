#!/usr/bin/env python3
"""
rank_villages.py - Prioritize disaster-affected villages based on satellite change masks,
population estimates, road blockage severity, and hospital accessibility.

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
# NAMED CONSTANTS & POPULATION WEIGHTS
# =============================================================================

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

    # Construct clean Overpass QL
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


def get_change_mask_dataset(data_dir: Path, rivers_gdf: gpd.GeoDataFrame, utm_epsg: str) -> tuple[np.ndarray, rasterio.Affine, str, rasterio.io.DatasetReader]:
    """
    Returns (mask_array, transform, crs, raster_dataset).
    If data/change_mask.tif exists, loads it.
    Otherwise, creates data/dummy_change_mask.tif on the grid of data/sikkim_srtm.tif
    by rasterizing rivers buffered by 300m in UTM, and prints a loud warning.
    """
    real_mask_path = data_dir / "change_mask.tif"
    dummy_mask_path = data_dir / "dummy_change_mask.tif"
    srtm_path = data_dir / "sikkim_srtm.tif"

    if real_mask_path.exists():
        _log(f"Using change mask: {real_mask_path}")
        src = rasterio.open(real_mask_path)
        mask = (src.read(1) == 1)
        return mask, src.transform, src.crs, src

    # Print loud warning for dummy mask
    print("\n" + "=" * 70, flush=True)
    print("  WARNING: DUMMY MASK in use, not a real result", flush=True)
    print("=" * 70 + "\n", flush=True)

    if not srtm_path.exists():
        _log(f"ERROR: Base DEM raster not found at {srtm_path}")
        sys.exit(1)

    with rasterio.open(srtm_path) as srtm_src:
        profile = srtm_src.profile.copy()
        transform = srtm_src.transform
        crs = srtm_src.crs
        shape = srtm_src.shape

    _log(f"Creating dummy change mask on SRTM grid ({shape[0]}x{shape[1]})...")

    # Buffer rivers in UTM by 300 m
    if not rivers_gdf.empty:
        rivers_utm = rivers_gdf.to_crs(utm_epsg)
        buffered_rivers_utm = rivers_utm.buffer(RIVER_DUMMY_BUFFER_M)
        buffered_rivers_wgs84 = buffered_rivers_utm.to_crs(crs)
        combined_geom = unary_union(buffered_rivers_wgs84.geometry)
        geoms_to_rasterize = [mapping(combined_geom)] if not combined_geom.is_empty else []
    else:
        line = LineString([(88.55, 27.75), (88.53, 27.50), (88.48, 27.30), (88.40, 27.15)])
        line_utm = gpd.GeoSeries([line], crs="EPSG:4326").to_crs(utm_epsg).buffer(300.0).to_crs(crs).iloc[0]
        geoms_to_rasterize = [mapping(line_utm)]

    if geoms_to_rasterize:
        dummy_mask = rasterize(
            shapes=((g, 1) for g in geoms_to_rasterize),
            out_shape=shape,
            transform=transform,
            fill=0,
            dtype=np.uint8,
        )
    else:
        dummy_mask = np.zeros(shape, dtype=np.uint8)

    profile.update(dtype=rasterio.uint8, count=1, nodata=0)
    with rasterio.open(dummy_mask_path, "w", **profile) as dst:
        dst.write(dummy_mask, 1)
    _log(f"  -> Saved {dummy_mask_path}")

    src = rasterio.open(dummy_mask_path)
    mask = (dummy_mask == 1)
    return mask, transform, crs, src


def sample_mask_at_point(x_coord: float, y_coord: float, mask: np.ndarray, transform: rasterio.Affine) -> int:
    """Sample binary mask at given (x, y) coordinates."""
    try:
        r, c = rowcol(transform, x_coord, y_coord)
        if 0 <= r < mask.shape[0] and 0 <= c < mask.shape[1]:
            return 1 if mask[r, c] else 0
    except Exception:
        pass
    return 0


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

    # 2. Get change mask
    mask, mask_transform, mask_crs, mask_src = get_change_mask_dataset(data_dir, rivers_raw, utm_epsg)

    # 3. Prepare geometric layers in UTM & WGS84
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

    # 4. Compute metrics per village
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

        try:
            masked_data, _ = rasterio_mask(mask_src, [mapping(circle_wgs84)], crop=True, nodata=255)
            valid_pixels = masked_data[0][masked_data[0] != 255]
            if len(valid_pixels) > 0:
                changed_pixels = np.count_nonzero(valid_pixels == 1)
                affected_fraction = float(changed_pixels / len(valid_pixels))
            else:
                affected_fraction = 0.0
        except Exception:
            affected_fraction = 0.0

        # C. Blocked-road share (sampled every 50m along roads within 2 km in UTM)
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

        # D. Hospital distance to nearest unaffected hospital
        if unaffected_hospitals_utm:
            min_hosp_dist_m = min(v_pt_utm.distance(h_pt) for h_pt in unaffected_hospitals_utm)
            hosp_dist_km = min_hosp_dist_m / 1000.0
            hosp_str = f"nearest unaffected hospital {int(round(hosp_dist_km))} km away"
        else:
            hosp_dist_km = HOSPITAL_MAX_DIST_KM
            hosp_str = "no unaffected hospital mapped"

        # E. Composite Score
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

        # F. Plain-language reason string
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
            "geometry": v_pt_wgs84,
        })

    mask_src.close()

    # 5. Filter: keep only villages with score > 0
    gdf_all = gpd.GeoDataFrame(ranked_records, crs="EPSG:4326")
    gdf_positive = gdf_all[gdf_all["score"] > 0.0].copy()

    # Sort descending by score
    gdf_sorted = gdf_positive.sort_values(by="score", ascending=False).reset_index(drop=True)
    gdf_sorted["rank"] = gdf_sorted.index + 1

    # Keep exact required properties: rank, name, population, score, reason
    output_gdf = gdf_sorted[["rank", "name", "population", "score", "reason", "geometry"]].copy()

    # 6. Save GeoJSON outputs
    data_dir.mkdir(parents=True, exist_ok=True)
    out_file_data = data_dir / "villages_ranked.geojson"
    output_gdf.to_file(out_file_data, driver="GeoJSON")
    _log(f"Saved {len(output_gdf)} ranked villages -> {out_file_data}")

    try:
        frontend_dir.mkdir(parents=True, exist_ok=True)
        out_file_frontend = frontend_dir / "villages_ranked.geojson"
        output_gdf.to_file(out_file_frontend, driver="GeoJSON")
        _log(f"Saved {len(output_gdf)} ranked villages -> {out_file_frontend}")
    except Exception as e:
        _log(f"  [WARN] Could not copy to frontend dir: {e}")

    # 7. Print top 10 rows and total count
    print("\n" + "=" * 95, flush=True)
    print(f"  TOP 10 RANKED VILLAGES (Total with Score > 0: {len(output_gdf)} / {len(gdf_all)})", flush=True)
    print("=" * 95, flush=True)
    print(f"{'Rank':<6} {'Name':<24} {'Pop':<8} {'Score':<8} {'Reason'}", flush=True)
    print("-" * 95, flush=True)
    for _, row in output_gdf.head(10).iterrows():
        print(f"#{row['rank']:<5} {row['name'][:22]:<24} {row['population']:<8} {row['score']:<8.2f} {row['reason']}", flush=True)
    print("=" * 95 + "\n", flush=True)


if __name__ == "__main__":
    main()
