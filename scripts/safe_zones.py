#!/usr/bin/env python3
"""
safe_zones.py - Identify post-disaster safe zones in the Sikkim / Teesta valley region.

Criteria for a safe zone:
  1. Terrain slope < 15 degrees   (from SRTM DEM)
  2. Distance to nearest river > 200 m
  3. Distance to nearest road  < 500 m

Data sources:
  - OpenStreetMap (via osmnx / Overpass) -> roads, hospitals, shelters/schools, villages, rivers
  - data/sikkim_srtm.tif                -> SRTM 30 m DEM

Output:
  data/safe_zones.geojson               -> GeoJSON with fields: name, type, lat, lon
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
import requests
from rasterio.transform import rowcol
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

warnings.filterwarnings("ignore")

# -- Configuration ------------------------------------------------------------
BBOX = (88.30, 27.15, 88.75, 27.75)        # west, south, east, north
WEST, SOUTH, EAST, NORTH = BBOX

SLOPE_THRESHOLD_DEG = 15.0     # maximum safe slope (degrees)
RIVER_BUFFER_M      = 200.0    # minimum distance from rivers (metres)
ROAD_BUFFER_M       = 500.0    # maximum distance to a road (metres)

ROOT_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT_DIR / "data"
DEM_PATH   = DATA_DIR / "sikkim_srtm.tif"
OUTPUT_PATH = DATA_DIR / "safe_zones.geojson"

# UTM zone 45N covers Sikkim - used for accurate metre-based buffering
CRS_METRIC = "EPSG:32645"

# Configure osmnx
ox.settings.http_user_agent = "PostDisasterIntelligence/1.0 (disaster-relief; contact@relief.org)"
ox.settings.requests_timeout = 60
ox.settings.use_cache = True


# -- Helpers ------------------------------------------------------------------

def _log(msg: str) -> None:
    try:
        print(f"[safe_zones] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[safe_zones] {msg.encode('ascii', errors='replace').decode('ascii')}", flush=True)


def compute_slope_degrees(dem_path: Path) -> tuple:
    """
    Read the DEM and return (slope_array_degrees, transform, crs, shape).
    Slope is computed via numpy gradient on the elevation grid.
    """
    _log(f"Reading DEM from {dem_path}")
    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(np.float32)
        transform = src.transform
        crs = src.crs
        nodata = src.nodata

    # Mask nodata
    if nodata is not None:
        dem[dem == nodata] = np.nan

    # Pixel resolution in metres (approximate for geographic CRS)
    # At ~27 deg N, 1 deg lat ~ 111,320 m, 1 deg lon ~ cos(27)*111,320 ~ 99,150 m
    res_y = abs(transform.e)
    res_x = abs(transform.a)
    lat_centre = (NORTH + SOUTH) / 2.0
    dy = res_y * 111_320.0
    dx = res_x * 111_320.0 * np.cos(np.radians(lat_centre))

    # Gradient -> slope in degrees
    grad_y, grad_x = np.gradient(dem, dy, dx)
    slope = np.degrees(np.arctan(np.sqrt(grad_x**2 + grad_y**2)))

    _log(f"Slope range: {np.nanmin(slope):.1f} deg - {np.nanmax(slope):.1f} deg")
    return slope, transform, crs, dem.shape


# -- Fast OSM Fetcher (Single Overpass Query with geom) ------------------------

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

def fetch_osm_data_batch() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Fetches roads, rivers, hospitals, shelters/schools, villages, and water sources
    in a single comprehensive Overpass API request with geometric coordinates.
    """
    _log("Querying OpenStreetMap data for Sikkim bounding box...")

    query = f"""
    [out:json][timeout:90];
    (
      // Roads
      way["highway"~"primary|secondary|tertiary|trunk|motorway|residential|unclassified|service|track"]({SOUTH},{WEST},{NORTH},{EAST});
      
      // Rivers & Waterways
      way["waterway"~"river|stream|canal"]({SOUTH},{WEST},{NORTH},{EAST});
      relation["waterway"~"river|stream|canal"]({SOUTH},{WEST},{NORTH},{EAST});
      
      // Hospitals & Health facilities
      node["amenity"~"hospital|clinic|doctors"]({SOUTH},{WEST},{NORTH},{EAST});
      way["amenity"~"hospital|clinic|doctors"]({SOUTH},{WEST},{NORTH},{EAST});
      
      // Shelters, Schools, Community Centres, Places of Worship
      node["amenity"~"shelter|school|community_centre|place_of_worship|kindergarten|college"]({SOUTH},{WEST},{NORTH},{EAST});
      way["amenity"~"shelter|school|community_centre|place_of_worship|kindergarten|college"]({SOUTH},{WEST},{NORTH},{EAST});
      
      // Villages & Settlements
      node["place"~"village|hamlet|town|isolated_dwelling"]({SOUTH},{WEST},{NORTH},{EAST});
      
      // Drinking water / Safe water sources
      node["amenity"~"drinking_water|water_point"]({SOUTH},{WEST},{NORTH},{EAST});
      node["man_made"~"water_well|water_tap|spring_box"]({SOUTH},{WEST},{NORTH},{EAST});
      node["natural"="spring"]({SOUTH},{WEST},{NORTH},{EAST});
    );
    out body geom;
    """

    headers = {
        "User-Agent": "PostDisasterIntelligence/1.0 (disaster-relief; contact@relief.org)",
    }

    data = None
    for server in OVERPASS_SERVERS:
        try:
            _log(f"  Attempting query via {server} ...")
            resp = requests.post(server, data={"data": query}, headers=headers, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                _log(f"  -> Successfully retrieved {len(data.get('elements', []))} OSM elements")
                break
            else:
                _log(f"  [WARN] Server responded with status {resp.status_code}")
        except Exception as e:
            _log(f"  [WARN] Query failed on {server}: {e}")
            time.sleep(2)

    if not data or "elements" not in data:
        _log("  [WARN] Direct Overpass query failed. Falling back to osmnx download ...")
        return fallback_osmnx_downloads()

    return parse_overpass_elements(data["elements"])


def parse_overpass_elements(elements: list) -> tuple:
    """Parse raw Overpass JSON elements into GeoDataFrames."""
    roads_list = []
    rivers_list = []
    hospitals_list = []
    shelters_list = []
    villages_list = []
    water_list = []

    for el in elements:
        tags = el.get("tags", {})
        el_type = el.get("type")
        geom = None

        if el_type == "node":
            lat, lon = el.get("lat"), el.get("lon")
            if lat is not None and lon is not None:
                geom = Point(lon, lat)
        elif el_type in ("way", "relation") and "geometry" in el:
            pts = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(pts) >= 2:
                # Check if it's a closed polygon
                if pts[0] == pts[-1] and len(pts) >= 4 and ("amenity" in tags or "building" in tags):
                    geom = Polygon(pts)
                else:
                    geom = LineString(pts)

        if geom is None:
            continue

        name = tags.get("name") or tags.get("name:en") or tags.get("official_name") or tags.get("alt_name") or "Unnamed"

        # Categorize
        if "highway" in tags:
            roads_list.append({"name": name, "geometry": geom})
        if "waterway" in tags:
            rivers_list.append({"name": name, "geometry": geom})
        
        amenity = tags.get("amenity", "")
        if amenity in ("hospital", "clinic", "doctors"):
            hospitals_list.append({"name": name, "geometry": geom, "tags": tags})
        elif amenity in ("shelter", "school", "community_centre", "place_of_worship", "kindergarten", "college"):
            shelters_list.append({"name": name, "geometry": geom, "tags": tags})

        if "place" in tags and tags["place"] in ("village", "hamlet", "town", "isolated_dwelling"):
            villages_list.append({"name": name, "geometry": geom, "tags": tags})

        if (amenity in ("drinking_water", "water_point") or 
            tags.get("man_made") in ("water_well", "water_tap", "spring_box") or 
            tags.get("natural") == "spring"):
            water_list.append({"name": name, "geometry": geom, "tags": tags})

    def to_gdf(records):
        if not records:
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        return gpd.GeoDataFrame(records, crs="EPSG:4326")

    roads_gdf = to_gdf(roads_list)
    rivers_gdf = to_gdf(rivers_list)
    hospitals_gdf = to_gdf(hospitals_list)
    shelters_gdf = to_gdf(shelters_list)
    villages_gdf = to_gdf(villages_list)
    water_gdf = to_gdf(water_list)

    _log(f"  Parsed OSM layers: {len(roads_gdf)} roads, {len(rivers_gdf)} rivers, {len(hospitals_gdf)} hospitals, {len(shelters_gdf)} shelters/schools, {len(villages_gdf)} villages, {len(water_gdf)} water sources")

    return roads_gdf, rivers_gdf, hospitals_gdf, shelters_gdf, villages_gdf, water_gdf


def fallback_osmnx_downloads() -> tuple:
    """Fallback using OSMnx with try-catch blocks."""
    _log("Downloading via OSMnx...")
    try:
        G = ox.graph_from_bbox(bbox=(WEST, SOUTH, EAST, NORTH), network_type="drive", truncate_by_edge=True)
        roads = ox.graph_to_gdfs(G, nodes=False, edges=True)
    except Exception as e:
        _log(f"  [WARN] Road download failed: {e}")
        roads = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    def _get_feat(tags, label):
        try:
            return ox.features_from_bbox(bbox=(WEST, SOUTH, EAST, NORTH), tags=tags)
        except Exception as e:
            _log(f"  [WARN] {label} download failed: {e}")
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    hospitals = _get_feat({"amenity": "hospital"}, "hospitals")
    shelters = _get_feat({"amenity": ["shelter", "school", "community_centre", "place_of_worship"]}, "shelters")
    villages = _get_feat({"place": ["village", "hamlet", "town"]}, "villages")
    rivers = _get_feat({"waterway": ["river", "stream", "canal"]}, "rivers")
    water = _get_feat({"amenity": "drinking_water", "natural": "spring"}, "water")

    return roads, rivers, hospitals, shelters, villages, water


# -- Spatial filters ----------------------------------------------------------

def point_passes_slope(point: Point, slope: np.ndarray, transform) -> bool:
    """Check whether a point lies on a DEM pixel with slope < threshold."""
    try:
        r, c = rowcol(transform, point.x, point.y)
        if 0 <= r < slope.shape[0] and 0 <= c < slope.shape[1]:
            val = slope[r, c]
            return not np.isnan(val) and val < SLOPE_THRESHOLD_DEG
    except Exception:
        pass
    return False


def filter_by_river_distance(
    gdf: gpd.GeoDataFrame, rivers: gpd.GeoDataFrame, min_dist_m: float
) -> gpd.GeoDataFrame:
    """Keep only features that are > min_dist_m from any river."""
    if rivers.empty or gdf.empty:
        return gdf

    rivers_m = rivers.to_crs(CRS_METRIC)
    gdf_m = gdf.to_crs(CRS_METRIC)
    river_union = unary_union(rivers_m.geometry)
    mask = gdf_m.geometry.distance(river_union) > min_dist_m
    return gdf.loc[mask].copy()


def filter_by_road_distance(
    gdf: gpd.GeoDataFrame, roads: gpd.GeoDataFrame, max_dist_m: float
) -> gpd.GeoDataFrame:
    """Keep only features that are < max_dist_m from a road."""
    if roads.empty or gdf.empty:
        return gdf

    roads_m = roads.to_crs(CRS_METRIC)
    gdf_m = gdf.to_crs(CRS_METRIC)
    road_union = unary_union(roads_m.geometry)
    mask = gdf_m.geometry.distance(road_union) < max_dist_m
    return gdf.loc[mask].copy()


def to_points(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure every geometry is a point (take centroid of polygons/lines)."""
    if gdf.empty:
        return gdf
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.centroid
    return gdf


# -- Main pipeline ------------------------------------------------------------

def main() -> None:
    if not DEM_PATH.exists():
        sys.exit(f"ERROR: DEM not found at {DEM_PATH}")

    # 1. Compute slope from DEM
    slope, transform, crs, shape = compute_slope_degrees(DEM_PATH)

    # 2. Download OSM layers
    roads, rivers, hospitals, shelters, villages, water_src = fetch_osm_data_batch()

    # 3. Build candidate points with type labels
    candidates = []

    def _add(gdf: gpd.GeoDataFrame, zone_type: str):
        if gdf.empty:
            return
        pts = to_points(gdf).to_crs("EPSG:4326")
        for _, row in pts.iterrows():
            name = row.get("name", "Unnamed")
            if not name or str(name).strip() == "" or str(name).lower() == "nan":
                name = "Unnamed"
            candidates.append({
                "name": str(name).strip(),
                "type": zone_type,
                "geometry": row.geometry,
            })

    _add(hospitals, "hospital")
    _add(shelters,  "shelter")
    _add(villages,  "shelter")      # villages can serve as community shelters
    _add(water_src, "water")

    if not candidates:
        _log("[WARN] No candidate features found from OSM. Writing empty GeoJSON.")
        empty = gpd.GeoDataFrame(
            {"name": [], "type": [], "lat": [], "lon": [], "geometry": []},
            crs="EPSG:4326",
        )
        empty.to_file(OUTPUT_PATH, driver="GeoJSON")
        return

    cand_gdf = gpd.GeoDataFrame(candidates, crs="EPSG:4326")
    _log(f"Total candidate points: {len(cand_gdf)}")

    # 4. Filter - slope < 15 degrees
    _log("Filtering by slope < 15 deg ...")
    slope_ok = cand_gdf.geometry.apply(
        lambda pt: point_passes_slope(pt, slope, transform)
    )
    cand_gdf = cand_gdf.loc[slope_ok].copy()
    _log(f"  -> {len(cand_gdf)} pass slope < {SLOPE_THRESHOLD_DEG} deg")

    # 5. Filter - river distance > 200 m
    _log("Filtering by river distance > 200 m ...")
    cand_gdf = filter_by_river_distance(cand_gdf, rivers, RIVER_BUFFER_M)
    _log(f"  -> {len(cand_gdf)} pass > {RIVER_BUFFER_M} m from rivers")

    # 6. Filter - road proximity < 500 m
    _log("Filtering by road proximity < 500 m ...")
    cand_gdf = filter_by_road_distance(cand_gdf, roads, ROAD_BUFFER_M)
    _log(f"  -> {len(cand_gdf)} pass < {ROAD_BUFFER_M} m from road")

    # 7. Add lat / lon columns & deduplicate
    cand_gdf["lon"] = np.round(cand_gdf.geometry.x, 6)
    cand_gdf["lat"] = np.round(cand_gdf.geometry.y, 6)

    # Keep only the required columns: name, type, lat, lon
    result = cand_gdf[["name", "type", "lat", "lon", "geometry"]].copy()
    result = result.reset_index(drop=True)

    # Remove exact-location duplicates
    result = result.drop_duplicates(subset=["lat", "lon"])
    _log(f"Final safe zones: {len(result)}")

    # 8. Save output
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result.to_file(OUTPUT_PATH, driver="GeoJSON")
    _log(f"Saved -> {OUTPUT_PATH}")

    # Summary
    _log("-- Summary --")
    for t in ("hospital", "shelter", "water"):
        count = (result["type"] == t).sum()
        _log(f"  {t:>10s}: {count}")


if __name__ == "__main__":
    main()
