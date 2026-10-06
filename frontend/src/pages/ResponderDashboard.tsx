import React, { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import {
  getRankedVillages,
  MONITORED_SITES,
  SiteInfo,
  VillageFeature,
  VillageFeatureCollection,
} from "@/lib/data"
import { StatBar } from "@/components/StatBar"
import { SiteSwitcher } from "@/components/SiteSwitcher"
import { RankedCard } from "@/components/RankedCard"
import { LayerToggles, LayerState } from "@/components/LayerToggles"
import { ConfidenceLegend } from "@/components/ConfidenceLegend"
import { SwipeSlider } from "@/components/SwipeSlider"
import {
  Activity,
  Compass,
  Download,
  Filter,
  Maximize2,
  Radio,
  RefreshCw,
  Search,
  Shield,
  Smartphone,
  SlidersHorizontal,
  Layers,
  MapPin,
  AlertTriangle,
  FileText,
} from "lucide-react"

export const ResponderDashboard: React.FC = () => {
  const [currentSite, setCurrentSite] = useState<SiteInfo>(MONITORED_SITES[0])
  const [villages, setVillages] = useState<VillageFeature[]>([])
  const [selectedVillage, setSelectedVillage] = useState<VillageFeature | null>(null)
  const [dataSource, setDataSource] = useState<"supabase" | "local">("local")
  const [loading, setLoading] = useState<boolean>(true)
  const [filterTab, setFilterTab] = useState<string>("ALL")
  const [searchQuery, setSearchQuery] = useState<string>("")

  // Swipe slider state
  const [sliderValue, setSliderValue] = useState<number>(50)
  const [isSplitEngaged, setIsSplitEngaged] = useState<boolean>(true)

  // Layer toggles state
  const [layers, setLayers] = useState<LayerState>({
    changeActive: true,
    riskOverlay: true,
    priorityNodes: true,
    safeZones: true,
  })

  // Load data
  useEffect(() => {
    let isMounted = true
    setLoading(true)

    getRankedVillages(currentSite.id)
      .then((res) => {
        if (!isMounted) return
        setVillages(res.data.features || [])
        setDataSource(res.source)
        if (res.data.features && res.data.features.length > 0) {
          setSelectedVillage(res.data.features[0])
        } else {
          setSelectedVillage(null)
        }
      })
      .catch((err) => {
        console.error("Failed to load villages:", err)
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [currentSite])

  const handleToggleLayer = (layer: keyof LayerState) => {
    setLayers((prev) => ({
      ...prev,
      [layer]: !prev[layer],
    }))
  }

  // Filter villages
  const filteredVillages = villages.filter((v) => {
    const p = v.properties
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchesName = p.name.toLowerCase().includes(q)
      const matchesReason = p.reason.toLowerCase().includes(q)
      const matchesRegion = p.region?.toLowerCase().includes(q)
      if (!matchesName && !matchesReason && !matchesRegion) return false
    }

    if (filterTab === "CRITICAL") return p.priority === "CRITICAL" || p.score >= 0.9
    if (filterTab === "DAM BASIN") return p.region?.includes("Basin") || p.reason.includes("dam")
    if (filterTab === "NH-10") return p.region?.includes("NH-10") || p.reason.includes("NH-10") || p.roadStatus?.includes("NH-10")
    return true
  })

  return (
    <div className="min-h-screen bg-[#08090d] text-neutral-100 flex flex-col font-sans selection:bg-neutral-800 selection:text-white">
      {/* 1. Tactical Header */}
      <header className="bg-neutral-950 border-b border-neutral-800/80 px-4 py-2.5 flex flex-wrap items-center justify-between gap-y-3 z-30 font-mono">
        {/* Brand & Sector */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded bg-red-600/20 border border-red-500/40 flex items-center justify-center shadow-inner">
            <Radio className="w-4 h-4 text-red-500 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold tracking-wider text-sm sm:text-base text-neutral-100">
                EPICENTER
              </span>
              <span className="hidden sm:inline-block px-1.5 py-0.2 rounded bg-neutral-900 border border-neutral-800 text-[10px] text-neutral-400 font-semibold">
                v2.4-SAR
              </span>
            </div>
            <div className="text-[10px] tracking-tight text-neutral-400 hidden xs:block">
              CHANGE INTEL // RESPONDER CONSOLE
            </div>
          </div>

          <div className="h-5 w-px bg-neutral-800 hidden md:block" />

          {/* Site Switcher */}
          <div className="hidden sm:block">
            <SiteSwitcher
              currentSite={currentSite}
              onSelectSite={(site) => setCurrentSite(site)}
            />
          </div>
        </div>

        {/* Center Sector Coordinates & SAR Lock */}
        <div className="hidden xl:flex items-center space-x-3 text-xs bg-neutral-900/60 border border-neutral-800/80 px-3 py-1.5 rounded-sm">
          <span className="text-neutral-300 font-semibold">{currentSite.coordinates}</span>
          <span className="text-neutral-600">//</span>
          <span className="text-emerald-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>{currentSite.sarLockDesc}</span>
          </span>
        </div>

        {/* Right Navigation & Tools */}
        <div className="flex items-center space-x-2 text-xs">
          {/* Quick link to Mobile Citizen Mode */}
          <Link
            to="/citizen"
            className="flex items-center space-x-1.5 bg-neutral-900 hover:bg-neutral-800 text-neutral-200 border border-neutral-700 px-2.5 py-1.5 rounded text-xs transition-colors shadow-sm"
            title="Switch to Mobile-First Citizen Mode"
          >
            <Smartphone className="w-3.5 h-3.5 text-neutral-300" />
            <span className="font-semibold hidden sm:inline">Citizen Mode</span>
          </Link>

          {/* Navigation Pill Tabs */}
          <div className="hidden lg:flex items-center bg-neutral-900/80 border border-neutral-800 rounded p-0.5">
            <button className="px-2.5 py-1 rounded bg-neutral-800 text-neutral-100 font-medium text-[11px]">
              Tactical Console
            </button>
            <button className="px-2.5 py-1 text-neutral-400 hover:text-neutral-200 text-[11px] transition-colors">
              Priority Matrix
            </button>
            <button className="px-2.5 py-1 text-neutral-400 hover:text-neutral-200 text-[11px] transition-colors">
              SAR Telemetry
            </button>
          </div>
        </div>
      </header>

      {/* 2. StatBar Telemetry Strip */}
      <StatBar
        affectedAreaKm2={currentSite.affectedAreaKm2}
        affectedDeltaKm2={currentSite.affectedDeltaKm2}
        peopleAtRisk={currentSite.peopleAtRisk}
        criticalNodes={villages.length || currentSite.criticalNodes}
      />

      {/* 3. Main Workspace: Split into Left Triage Panel and Right Map Canvas */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
        {/* Left Sidebar: Ranked Village Triage Panel */}
        <aside className="w-full lg:w-[420px] xl:w-[460px] bg-[#0c0e14] border-r border-neutral-800 flex flex-col shrink-0 z-20 max-h-[50vh] lg:max-h-[calc(100vh-105px)] overflow-hidden font-mono">
          {/* Triage Panel Header */}
          <div className="p-3.5 border-b border-neutral-800/80 bg-neutral-950/60">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                <h2 className="text-xs font-bold uppercase tracking-wider text-neutral-100">
                  GO HERE FIRST
                </h2>
                <span className="px-1.5 py-0.5 rounded text-[9px] bg-red-950 text-red-400 border border-red-900 font-bold">
                  SYS-RANKED
                </span>
              </div>
              <span className="text-[10px] text-neutral-400">
                {filteredVillages.length} SECTORS
              </span>
            </div>

            <p className="text-[11px] text-neutral-400 leading-tight">
              Ranked priority based on SAR water surge &amp; road severance.
            </p>
            <div className="text-[10px] text-neutral-400 mt-1 flex items-center justify-between">
              <span>Sorted by Exposure Index (Desc)</span>
              <span className="text-[9px] text-neutral-400">
                Data: {dataSource === "supabase" ? "Supabase Cloud" : "Local GeoJSON"}
              </span>
            </div>

            {/* Search and Filters */}
            <div className="mt-3 space-y-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter sector name, dam, bridge..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-neutral-900 border border-neutral-800 rounded pl-8 pr-3 py-1.5 text-xs text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-neutral-600"
                />
              </div>

              {/* Filter Tabs */}
              <div className="flex items-center space-x-1 text-[10px]">
                {["ALL", "CRITICAL", "DAM BASIN", "NH-10"].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setFilterTab(tab)}
                    className={`px-2 py-1 rounded transition-colors ${
                      filterTab === tab
                        ? "bg-neutral-800 text-neutral-100 font-bold border border-neutral-700"
                        : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900"
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Cards Scrollable List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {loading ? (
              <div className="py-12 text-center text-xs text-neutral-500">
                <RefreshCw className="w-5 h-5 mx-auto animate-spin text-neutral-400 mb-2" />
                <span>Loading satellite triage priorities...</span>
              </div>
            ) : filteredVillages.length === 0 ? (
              <div className="py-12 text-center text-xs text-neutral-500">
                <span>No sectors match criteria</span>
              </div>
            ) : (
              filteredVillages.map((village) => (
                <RankedCard
                  key={village.properties.rank}
                  feature={village}
                  isSelected={selectedVillage?.properties.rank === village.properties.rank}
                  onSelect={(v) => setSelectedVillage(v)}
                />
              ))
            )}
          </div>

          {/* Panel Footer */}
          <div className="p-2.5 bg-neutral-950 border-t border-neutral-800 text-[10px] text-neutral-400 flex items-center justify-between">
            <span className="flex items-center space-x-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>RADAR PASS: S1B_IW_GRDH 03-OCT 22:48 UTC</span>
            </span>
            <span className="text-neutral-400">12ms LATENCY</span>
          </div>
        </aside>

        {/* Right Map Canvas & Tactical HUD Overlay */}
        <div className="flex-1 relative flex flex-col bg-neutral-950 overflow-hidden min-h-[500px]">
          {/* MapLibre Placeholder DIV with Tactical GIS Visual Simulation */}
          <div
            id="maplibre-placeholder"
            className="absolute inset-0 w-full h-full bg-[#07090e] tactical-grid-bg overflow-hidden select-none"
          >
            {/* Visual GIS simulation background */}
            <div className="absolute inset-0 opacity-40 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-950/30 via-[#07090e] to-black" />

            {/* Simulated River Vector Path & Flood Envelope */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <linearGradient id="riverGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.4" />
                  <stop offset="50%" stopColor="#ef4444" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.5" />
                </linearGradient>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="glow" />
                  <feComposite in="SourceGraphic" in2="glow" operator="over" />
                </filter>
              </defs>

              {/* Teesta River Main Spine */}
              <path
                d="M 180,40 Q 260,180 320,290 T 480,420 T 560,620 T 640,820"
                fill="none"
                stroke="url(#riverGradient)"
                strokeWidth={layers.changeActive ? "14" : "4"}
                strokeLinecap="round"
                filter="url(#glow)"
                className="transition-all duration-700"
              />

              {/* Flood Inundation Contour Bands */}
              {layers.riskOverlay && (
                <>
                  <path
                    d="M 160,35 Q 240,170 300,285 T 460,410 T 540,610 T 620,810"
                    fill="none"
                    stroke="#dc2626"
                    strokeWidth="3"
                    strokeDasharray="6 4"
                    opacity="0.7"
                    className="animate-pulse"
                  />
                  <path
                    d="M 200,45 Q 280,190 340,295 T 500,430 T 580,630 T 660,830"
                    fill="none"
                    stroke="#ea580c"
                    strokeWidth="2"
                    strokeDasharray="4 4"
                    opacity="0.6"
                  />
                </>
              )}
            </svg>

            {/* Split Swipe Vertical Line simulation */}
            {isSplitEngaged && (
              <div
                className="absolute top-0 bottom-0 pointer-events-none z-10 transition-all duration-75"
                style={{ left: `${sliderValue}%` }}
              >
                <div className="w-0.5 h-full bg-white/70 shadow-[0_0_10px_rgba(255,255,255,0.8)]" />
                <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-neutral-900 border-2 border-white flex items-center justify-center text-[10px] text-white shadow-xl">
                  ↔
                </div>
              </div>
            )}

            {/* Interactive Node Markers placed on the simulated map */}
            <div className="absolute inset-0 pointer-events-auto">
              {layers.priorityNodes &&
                villages.map((v, index) => {
                  const isCur = selectedVillage?.properties.rank === v.properties.rank
                  // Pseudo coordinates mapped across canvas area
                  const positions = [
                    { top: "28%", left: "38%" },
                    { top: "42%", left: "46%" },
                    { top: "58%", left: "53%" },
                    { top: "72%", left: "59%" },
                    { top: "35%", left: "49%" },
                    { top: "18%", left: "32%" },
                    { top: "22%", left: "62%" },
                  ]
                  const pos = positions[index % positions.length]

                  return (
                    <div
                      key={v.properties.rank}
                      style={{ top: pos.top, left: pos.left }}
                      onClick={() => setSelectedVillage(v)}
                      className={`absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group transition-transform ${
                        isCur ? "scale-125 z-30" : "hover:scale-110 z-20"
                      }`}
                    >
                      <div className="relative flex items-center justify-center">
                        {/* Outer pulse */}
                        {isCur && (
                          <div className="absolute w-8 h-8 rounded-full bg-red-500/30 animate-ping pointer-events-none" />
                        )}
                        <div
                          className={`w-6 h-6 rounded-full flex items-center justify-center border font-mono text-[10px] font-bold shadow-lg ${
                            v.properties.priority === "CRITICAL"
                              ? "bg-red-600 border-white text-white"
                              : v.properties.priority === "HIGH"
                              ? "bg-orange-500 border-white text-white"
                              : "bg-neutral-800 border-neutral-400 text-neutral-200"
                          }`}
                        >
                          #{v.properties.rank}
                        </div>
                      </div>

                      {/* Tooltip on hover */}
                      <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 hidden group-hover:block bg-neutral-950/95 border border-neutral-700 px-2 py-1 rounded text-[10px] font-mono text-white whitespace-nowrap shadow-xl">
                        {v.properties.name}
                      </div>
                    </div>
                  )
                })}
            </div>

            {/* MapLibre Tech Placeholder Stamp */}
            <div className="absolute top-4 left-4 pointer-events-none font-mono text-[10px] text-neutral-400 bg-neutral-950/70 border border-neutral-800/80 px-2.5 py-1.5 rounded">
              <span className="text-neutral-400">MAP ENGINE: </span>
              <span className="text-neutral-200 font-bold">MapLibre GL [Placeholder Ready]</span>
              <span className="block text-[9px] text-neutral-400">
                Extent: 88.30°E to 88.75°E, 27.15°N to 27.75°N
              </span>
            </div>
          </div>

          {/* Tactical HUD: Top Right Layer Toggles */}
          <div className="absolute top-4 right-4 z-20">
            <LayerToggles layers={layers} onToggle={handleToggleLayer} />
          </div>

          {/* Tactical HUD: Floating Pinpoint Details for Selected Village */}
          {selectedVillage && (
            <div className="absolute top-16 left-6 z-20 max-w-sm bg-neutral-950/95 border border-neutral-700 p-3 rounded shadow-2xl font-mono text-xs backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-neutral-800 pb-2 mb-2">
                <div className="flex items-center space-x-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                  <span className="font-bold text-neutral-100 text-xs uppercase">
                    {selectedVillage.properties.name} PINPOINT
                  </span>
                </div>
                <span className="text-[10px] text-neutral-400">
                  {selectedVillage.geometry.coordinates[1].toFixed(3)}°N,{" "}
                  {selectedVillage.geometry.coordinates[0].toFixed(3)}°E
                </span>
              </div>

              {/* Projected risk & river stage */}
              <div className="space-y-1.5 text-[11px]">
                <div className="bg-red-950/50 border border-red-900/60 p-1.5 rounded text-red-300 font-semibold flex items-center justify-between">
                  <span>Rainfall Risk (Next 72h):</span>
                  <span>{selectedVillage.properties.rainfallRisk || "HIGH RISK: 114mm"}</span>
                </div>

                <div className="flex items-center justify-between text-neutral-300 px-1">
                  <span className="text-neutral-400">River Gauge Stage:</span>
                  <span className="font-bold text-amber-400">
                    {selectedVillage.properties.riverGauge || "+4.8m (Breached)"}
                  </span>
                </div>

                <div className="text-[10px] text-neutral-400 pt-1 border-t border-neutral-900 flex items-center justify-between">
                  <span className="flex items-center space-x-1">
                    <Shield className="w-3 h-3 text-emerald-400" />
                    <span>SAR sensor lock verified</span>
                  </span>
                  <span className="text-neutral-300 font-bold">Triage Ops</span>
                </div>
              </div>
            </div>
          )}

          {/* Tactical HUD: Bottom Control Overlays */}
          <div className="absolute bottom-10 left-4 right-4 z-20 flex flex-col md:flex-row items-end justify-between gap-4 pointer-events-none">
            {/* Confidence Legend (Left) */}
            <div className="pointer-events-auto">
              <ConfidenceLegend score={96.8} radarPassTime="03-OCT 22:48 UTC" />
            </div>

            {/* Swipe Slider (Right) */}
            <div className="pointer-events-auto w-full md:w-auto">
              <SwipeSlider
                value={sliderValue}
                onChange={(val) => setSliderValue(val)}
                isSplitEngaged={isSplitEngaged}
                onToggleSplit={() => setIsSplitEngaged(!isSplitEngaged)}
                surgeDeltaText="+184% water extent"
              />
            </div>
          </div>

          {/* Tactical Status Strip (Bottommost Bar) */}
          <div className="absolute bottom-0 left-0 right-0 bg-neutral-950/95 border-t border-neutral-800/80 px-4 py-1.5 z-30 font-mono text-[10px] text-neutral-400 flex flex-wrap items-center justify-between gap-2">
            <div>
              <span>EPICENTER CRITICAL GIS DISASTER ENGINE // NODE 04-TEESTA // LATENCY: 12ms</span>
            </div>
            <div className="hidden sm:block">
              <span>COORDINATES: WGS84 EPSG:4326 // SECURITY LEVEL: FIELD CLEARANCE UNRESTRICTED</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
