import { createClient, SupabaseClient } from '@supabase/supabase-js'

export interface VillageProperties {
  rank: number
  name: string
  population: number
  score: number
  reason: string
  priority?: "CRITICAL" | "HIGH" | "ELEVATED" | "MONITORED" | "STABLE"
  region?: string
  waterSurgeDelta?: string
  isolatedCount?: string
  roadStatus?: string
  confidence?: string
  rainfallRisk?: string
  riverGauge?: string
}

export interface VillageFeature {
  type: "Feature"
  geometry: {
    type: "Point"
    coordinates: [number, number] // [lon, lat]
  }
  properties: VillageProperties
}

export interface VillageFeatureCollection {
  type: "FeatureCollection"
  features: VillageFeature[]
}

export type SafeZoneType = "hospital" | "shelter" | "water"

export interface SafeZoneProperties {
  name: string
  type: SafeZoneType
  lat: number
  lon: number
  subtitle?: string
  details?: string
  generator?: string
  potableSpring?: string
  elevationDelta?: string
  bearing?: string
  distanceKm?: number
  estWalkMinutes?: number
}

export interface SafeZoneFeature {
  type: "Feature"
  geometry: {
    type: "Point"
    coordinates: [number, number] // [lon, lat]
  }
  properties: SafeZoneProperties
}

export interface SafeZoneFeatureCollection {
  type: "FeatureCollection"
  features: SafeZoneFeature[]
}

export interface SiteInfo {
  id: string
  name: string
  label: string
  coordinates: string
  center: [number, number] // [lat, lon]
  status: "active" | "coming_soon"
  affectedAreaKm2: number
  affectedDeltaKm2: number
  peopleAtRisk: number
  criticalNodes: number
  sarLockDesc: string
}

export const MONITORED_SITES: SiteInfo[] = [
  {
    id: "sikkim",
    name: "Sikkim — Teesta River Flood (Oct 2023)",
    label: "Sikkim - Teesta River Flood (Oct 2023)",
    coordinates: "27.75° N 88.52° E",
    center: [27.75, 88.52],
    status: "active",
    affectedAreaKm2: 418.6,
    affectedDeltaKm2: 54.2,
    peopleAtRisk: 24858,
    criticalNodes: 14,
    sarLockDesc: "CLOUD-PENETRATING SAR LOCK",
  },
  {
    id: "kedarnath",
    name: "Kedarnath — Mandakini Basin (High Risk)",
    label: "Kedarnath - Mandakini Basin",
    coordinates: "30.73° N 79.06° E",
    center: [30.73, 79.06],
    status: "coming_soon",
    affectedAreaKm2: 0,
    affectedDeltaKm2: 0,
    peopleAtRisk: 0,
    criticalNodes: 0,
    sarLockDesc: "SATELLITE CALIBRATION PENDING",
  },
]

// Optional Supabase Client initialization without creating .env files
const supabaseUrl = (import.meta as any).env?.VITE_SUPABASE_URL || ""
const supabaseKey = (import.meta as any).env?.VITE_SUPABASE_ANON_KEY || ""

let supabase: SupabaseClient | null = null
if (supabaseUrl && supabaseKey) {
  try {
    supabase = createClient(supabaseUrl, supabaseKey)
  } catch (err) {
    console.warn("Supabase client init failed, will use local mock files:", err)
  }
}

/**
 * Fetch ranked villages: tries Supabase first, falls back to public/data/villages_ranked.geojson
 */
export async function getRankedVillages(siteId: string = "sikkim"): Promise<{
  data: VillageFeatureCollection
  source: "supabase" | "local"
}> {
  if (siteId === "kedarnath") {
    return {
      data: { type: "FeatureCollection", features: [] },
      source: "local",
    }
  }

  // 1. Try Supabase if initialized
  if (supabase) {
    try {
      const { data, error } = await supabase
        .from("villages_ranked")
        .select("*")
        .order("rank", { ascending: true })

      if (!error && data && data.length > 0) {
        // Transform Supabase rows into GeoJSON FeatureCollection if stored as tabular rows
        const features: VillageFeature[] = data.map((item: any) => ({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [item.lon ?? item.longitude ?? 88.647, item.lat ?? item.latitude ?? 27.604],
          },
          properties: {
            rank: item.rank,
            name: item.name,
            population: item.population,
            score: item.score,
            reason: item.reason,
            priority: item.priority,
            region: item.region,
            waterSurgeDelta: item.water_surge_delta ?? item.waterSurgeDelta,
            isolatedCount: item.isolated_count ?? item.isolatedCount,
            roadStatus: item.road_status ?? item.roadStatus,
            confidence: item.confidence,
            rainfallRisk: item.rainfall_risk ?? item.rainfallRisk,
            riverGauge: item.river_gauge ?? item.riverGauge,
          },
        }))
        return {
          data: { type: "FeatureCollection", features },
          source: "supabase",
        }
      }
    } catch (err) {
      console.warn("Supabase query failed, falling back to local geojson:", err)
    }
  }

  // 2. Fall back to local file
  try {
    const response = await fetch("/data/villages_ranked.geojson")
    if (!response.ok) {
      throw new Error(`Failed to load local villages geojson: ${response.status}`)
    }
    const json = (await response.json()) as VillageFeatureCollection
    return { data: json, source: "local" }
  } catch (err) {
    console.error("Failed to load local villages_ranked.geojson:", err)
    // Return empty fallback collection
    return {
      data: { type: "FeatureCollection", features: [] },
      source: "local",
    }
  }
}

/**
 * Fetch safe zones: tries Supabase first, falls back to public/data/safe_zones.geojson
 */
export async function getSafeZones(siteId: string = "sikkim"): Promise<{
  data: SafeZoneFeatureCollection
  source: "supabase" | "local"
}> {
  if (siteId === "kedarnath") {
    return {
      data: { type: "FeatureCollection", features: [] },
      source: "local",
    }
  }

  // 1. Try Supabase if initialized
  if (supabase) {
    try {
      const { data, error } = await supabase
        .from("safe_zones")
        .select("*")

      if (!error && data && data.length > 0) {
        const features: SafeZoneFeature[] = data.map((item: any) => ({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [item.lon ?? item.longitude, item.lat ?? item.latitude],
          },
          properties: {
            name: item.name,
            type: item.type,
            lat: item.lat ?? item.latitude,
            lon: item.lon ?? item.longitude,
            subtitle: item.subtitle,
            details: item.details,
            generator: item.generator,
            potableSpring: item.potable_spring ?? item.potableSpring,
            elevationDelta: item.elevation_delta ?? item.elevationDelta,
            bearing: item.bearing,
            distanceKm: item.distance_km ?? item.distanceKm,
            estWalkMinutes: item.est_walk_minutes ?? item.estWalkMinutes,
          },
        }))
        return {
          data: { type: "FeatureCollection", features },
          source: "supabase",
        }
      }
    } catch (err) {
      console.warn("Supabase query failed for safe zones, falling back to local geojson:", err)
    }
  }

  // 2. Fall back to local file
  try {
    const response = await fetch("/data/safe_zones.geojson")
    if (!response.ok) {
      throw new Error(`Failed to load local safe zones geojson: ${response.status}`)
    }
    const json = (await response.json()) as SafeZoneFeatureCollection
    return { data: json, source: "local" }
  } catch (err) {
    console.error("Failed to load local safe_zones.geojson:", err)
    return {
      data: { type: "FeatureCollection", features: [] },
      source: "local",
    }
  }
}
