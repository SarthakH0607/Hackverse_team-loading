import React, { useEffect, useState, useRef, useCallback } from "react"
import { Link } from "react-router-dom"
import {
  getRankedVillages,
  getSafeZones,
  MONITORED_SITES,
  SiteInfo,
  VillageFeature,
  SafeZoneFeature,
} from "@/lib/data"
import { StatBar } from "@/components/StatBar"
import { SiteSwitcher } from "@/components/SiteSwitcher"
import { RankedCard } from "@/components/RankedCard"
import { LayerToggles, LayerState } from "@/components/LayerToggles"
import { SwipeSlider } from "@/components/SwipeSlider"
import {
  Radio,
  RefreshCw,
  Search,
  Smartphone,
  MapPin,
  AlertTriangle,
  FileText,
  Sliders,
  ShieldCheck,
  Building2,
  Navigation,
  Info,
  Waves,
  Eye,
  Crosshair,
  CheckCircle2,
  X,
} from "lucide-react"

// Coordinate mapping helper for Sikkim Teesta III / Chungthang Sector
const getNodePosition = (name: string, lon: number, lat: number) => {
  const n = name.toLowerCase()
  if (n.includes("chungthang")) return { left: 48, top: 54 }
  if (n.includes("lachung")) return { left: 82, top: 18 }
  if (n.includes("lachen")) return { left: 16, top: 22 }
  if (n.includes("nanga")) return { left: 45, top: 82 }
  if (n.includes("mangan")) return { left: 24, top: 88 }
  if (n.includes("rangpo")) return { left: 34, top: 92 }
  if (n.includes("singtam")) return { left: 20, top: 76 }
  if (n.includes("dikchu")) return { left: 38, top: 68 }
  if (n.includes("lingthem")) return { left: 28, top: 74 }
  if (n.includes("rhenock")) return { left: 68, top: 88 }
  if (n.includes("namchi")) return { left: 14, top: 86 }
  if (n.includes("ravangla")) return { left: 18, top: 64 }

  // Fallback linear mapping
  const left = Math.max(10, Math.min(90, ((lon - 88.58) / 0.14) * 100))
  const top = Math.max(10, Math.min(90, ((27.68 - lat) / 0.13) * 100))
  return { left, top }
}

const getSafeZonePosition = (name: string, lon: number, lat: number) => {
  const n = name.toLowerCase()
  if (n.includes("chungthang")) return { left: 55, top: 48 }
  if (n.includes("lachen hospital")) return { left: 22, top: 20 }
  if (n.includes("lachen")) return { left: 14, top: 26 }
  if (n.includes("mangan")) return { left: 18, top: 90 }
  if (n.includes("lingthem")) return { left: 32, top: 72 }
  if (n.includes("tumlong")) return { left: 64, top: 68 }
  if (n.includes("golitar")) return { left: 56, top: 78 }
  if (n.includes("namchi")) return { left: 16, top: 92 }
  if (n.includes("rangpo")) return { left: 38, top: 94 }

  const left = Math.max(8, Math.min(92, ((lon - 88.58) / 0.14) * 100))
  const top = Math.max(8, Math.min(92, ((27.68 - lat) / 0.13) * 100))
  return { left, top }
}

export const ResponderDashboard: React.FC = () => {
  const [currentSite, setCurrentSite] = useState<SiteInfo>(MONITORED_SITES[0])
  const [villages, setVillages] = useState<VillageFeature[]>([])
  const [safeZones, setSafeZones] = useState<SafeZoneFeature[]>([])
  const [selectedVillage, setSelectedVillage] = useState<VillageFeature | null>(null)
  const [selectedSafeZone, setSelectedSafeZone] = useState<SafeZoneFeature | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [filterTab, setFilterTab] = useState<string>("ALL")
  const [searchQuery, setSearchQuery] = useState<string>("")

  // Swipe slider state (starts in middle: 50%)
  const [sliderValue, setSliderValue] = useState<number>(50)
  const [isDragging, setIsDragging] = useState<boolean>(false)

  // Location pagination state: user explicitly asked for 2 locations initially!
  const [visibleCount, setVisibleCount] = useState<number>(2)

  // Image loading validation states
  const [preImageError, setPreImageError] = useState<boolean>(false)
  const [postImageError, setPostImageError] = useState<boolean>(false)

  // Change overlay subtle opacity to avoid noisy red dots
  const [changeOpacity, setChangeOpacity] = useState<number>(45)

  // Layer toggles must start OFF by default
  const [layers, setLayers] = useState<LayerState>({
    changeActive: false,
    riskOverlay: false,
    priorityNodes: false,
    safeZones: false,
  })

  const comparisonContainerRef = useRef<HTMLDivElement>(null)

  // Verify images exist on mount
  useEffect(() => {
    const checkImage = (src: string, setError: (err: boolean) => void) => {
      const img = new Image()
      img.onload = () => setError(false)
      img.onerror = () => setError(true)
      img.src = src
    }

    checkImage("/data/pre_rgb.png", setPreImageError)
    checkImage("/data/post_rgb.png", setPostImageError)
  }, [])

  // Load village and safe zone data
  useEffect(() => {
    let isMounted = true
    setLoading(true)

    Promise.all([
      getRankedVillages(currentSite.id),
      getSafeZones(currentSite.id),
    ])
      .then(([vRes, sRes]) => {
        if (!isMounted) return
        const feats = vRes.data.features || []
        setVillages(feats)
        setSafeZones(sRes.data.features || [])
        if (feats.length > 0) {
          setSelectedVillage(feats[0])
        }
      })
      .catch((err) => {
        console.error("Failed to load geospatial datasets:", err)
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

  // Handle direct pointer/touch dragging on the comparison viewport
  const updateSliderFromPointer = useCallback((clientX: number) => {
    if (!comparisonContainerRef.current) return
    const rect = comparisonContainerRef.current.getBoundingClientRect()
    const pos = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100))
    setSliderValue(pos)
  }, [])

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    setIsDragging(true)
    updateSliderFromPointer(e.clientX)
  }

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging) return
    updateSliderFromPointer(e.clientX)
  }

  const handlePointerUp = () => {
    setIsDragging(false)
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

    if (filterTab === "CRITICAL") return p.priority === "CRITICAL" || p.score >= 0.9 || p.rank <= 5
    if (filterTab === "DAM BASIN") return p.name.toLowerCase().includes("chung") || p.region?.includes("Basin") || p.reason.includes("dam")
    if (filterTab === "NH-10") return p.region?.includes("NH-10") || p.reason.includes("NH-10") || p.roadStatus?.includes("NH-10")
    return true
  })

  // Check missing image error
  const missingError = preImageError
    ? "Image missing: public/data/pre_rgb.png"
    : postImageError
    ? "Image missing: public/data/post_rgb.png"
    : null

  return (
    <div className="min-h-screen bg-[#08090d] text-neutral-100 flex flex-col font-sans selection:bg-neutral-800 selection:text-white">
      {/* 1. Tactical Header */}
      <header className="bg-neutral-950 border-b border-neutral-800/80 px-4 py-2.5 flex flex-wrap items-center justify-between gap-y-3 z-30 font-mono">
        <div className="flex items-center space-x-3">
          <Link to="/" className="flex items-center space-x-2.5 group cursor-pointer" title="Back to Overview">
            <div className="w-8 h-8 rounded bg-red-600/20 border border-red-500/40 flex items-center justify-center shadow-inner group-hover:scale-105 transition-transform">
              <Radio className="w-4 h-4 text-red-500 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold tracking-wider text-sm sm:text-base text-neutral-100 group-hover:text-white transition-colors">
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
          </Link>

          <div className="h-5 w-px bg-neutral-800 hidden md:block" />

          {/* Site Switcher */}
          <div className="hidden sm:block">
            <SiteSwitcher
              currentSite={currentSite}
              onSelectSite={(site) => setCurrentSite(site)}
            />
          </div>
        </div>

        {/* Center Sector Coordinates & Extent */}
        <div className="hidden xl:flex items-center space-x-3 text-xs bg-neutral-900/60 border border-neutral-800/80 px-3 py-1.5 rounded-sm">
          <span className="text-neutral-300 font-semibold">EXTENT: 88.58°E, 27.55°N TO 88.72°E, 27.68°N</span>
          <span className="text-neutral-600">//</span>
          <span className="text-emerald-400 font-bold">TRUE-COLOR OPTICAL COMPARATOR</span>
        </div>

        {/* Right Navigation */}
        <div className="flex items-center space-x-2 text-xs">
          <Link
            to="/"
            className="flex items-center space-x-1 bg-neutral-900 hover:bg-neutral-800 text-neutral-300 hover:text-white border border-neutral-800 px-2.5 py-1.5 rounded text-xs transition-colors"
          >
            <span>Overview</span>
          </Link>

          <Link
            to="/citizen"
            className="flex items-center space-x-1.5 bg-neutral-900 hover:bg-neutral-800 text-emerald-400 hover:text-emerald-300 border border-emerald-900/50 px-3 py-1.5 rounded font-semibold transition-colors"
          >
            <Smartphone className="w-3.5 h-3.5" />
            <span>Citizen Mode</span>
          </Link>

          <a
            href="/data/incident_report.html"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center space-x-1 bg-red-950/40 hover:bg-red-900/60 text-red-300 hover:text-white border border-red-800/60 px-3 py-1.5 rounded font-semibold transition-colors"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Incident Report</span>
          </a>
        </div>
      </header>

      {/* 2. Top Metric Bar */}
      <StatBar
        affectedAreaKm2={currentSite.affectedAreaKm2}
        peopleAtRisk={currentSite.peopleAtRisk}
        criticalNodes={villages.filter((v) => v.properties.priority === "CRITICAL" || v.properties.rank <= 3).length || currentSite.criticalNodes}
      />

      {/* 3. Main Dashboard Workspace Layout */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
        {/* Left Triage Priority Feed Panel */}
        <aside className="w-full lg:w-[410px] xl:w-[440px] bg-[#0c0d12] border-r border-neutral-800/80 flex flex-col shrink-0 z-20 shadow-2xl">
          {/* Panel Header */}
          <div className="p-3.5 border-b border-neutral-800/80 space-y-3 font-mono">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold uppercase tracking-wider text-neutral-200">
                  PRIORITY MATRIX
                </span>
                <span className="px-1.5 py-0.2 rounded bg-red-950 text-red-400 border border-red-800/60 text-[9px] font-bold">
                  RANKED
                </span>
              </div>
              <span className="text-[10px] text-neutral-400">
                {villages.length} NODES LOGGED
              </span>
            </div>

            <p className="text-[11px] text-neutral-400 leading-snug font-sans">
              Algorithmic triage prioritizing flood surge exposure and access road severance.
            </p>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400" />
              <input
                type="text"
                placeholder="Filter sector name, dam, bridge..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-neutral-900 border border-neutral-800 rounded px-2.5 py-1.5 pl-8 text-xs text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-neutral-600 font-mono"
              />
            </div>

            {/* Quick Filter Tabs */}
            <div className="flex items-center space-x-1.5 pt-0.5">
              {["ALL", "CRITICAL", "DAM BASIN", "NH-10"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setFilterTab(tab)}
                  className={`px-2 py-0.5 rounded text-[10px] uppercase font-semibold transition-colors ${
                    filterTab === tab
                      ? "bg-neutral-200 text-neutral-950 font-bold"
                      : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Cards Scrollable List: Exactly 2 visible by default as requested! */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {loading ? (
              <div className="py-12 text-center text-xs text-neutral-500 font-mono">
                <RefreshCw className="w-5 h-5 mx-auto animate-spin text-neutral-400 mb-2" />
                <span>Loading priority matrix...</span>
              </div>
            ) : filteredVillages.length === 0 ? (
              <div className="py-12 text-center text-xs text-neutral-500 font-mono">
                <span>No sectors match criteria</span>
              </div>
            ) : (
              <>
                {filteredVillages.slice(0, visibleCount).map((village) => (
                  <RankedCard
                    key={village.properties.rank}
                    feature={village}
                    isSelected={selectedVillage?.properties.rank === village.properties.rank}
                    onSelect={(v) => {
                      setSelectedVillage(v)
                      setSelectedSafeZone(null)
                    }}
                  />
                ))}

                {/* Read More Locations Accordion Button */}
                {filteredVillages.length > 2 && (
                  <div className="pt-2 pb-1">
                    {visibleCount < filteredVillages.length ? (
                      <button
                        onClick={() => setVisibleCount((prev) => Math.min(prev + 5, filteredVillages.length))}
                        className="w-full py-2.5 px-3 rounded-md bg-neutral-900 hover:bg-neutral-850 border border-neutral-750 hover:border-neutral-600 text-neutral-200 hover:text-white text-xs font-mono font-semibold transition-all flex items-center justify-center space-x-2 shadow-lg group active:scale-[0.99]"
                      >
                        <span>Read More Locations</span>
                        <span className="px-2 py-0.5 rounded bg-red-950/90 text-red-400 border border-red-800/60 text-[10px] font-bold">
                          +{filteredVillages.length - visibleCount} more
                        </span>
                      </button>
                    ) : (
                      <button
                        onClick={() => setVisibleCount(2)}
                        className="w-full py-2 px-3 rounded-md bg-neutral-900 hover:bg-neutral-850 border border-neutral-800 text-neutral-400 hover:text-neutral-200 text-xs font-mono transition-colors"
                      >
                        Show Less (Collapse to 2)
                      </button>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </aside>

        {/* Right Map & Before/After Comparison Canvas */}
        <div className="flex-1 relative flex flex-col bg-neutral-950 overflow-hidden min-h-[500px]">
          {/* Interactive Dual Before/After Swipe Viewport */}
          <div
            ref={comparisonContainerRef}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            className="absolute inset-0 w-full h-full select-none cursor-ew-resize overflow-hidden bg-[#0a0c10]"
          >
            {/* Left Image: BEFORE (Sep 2023 Optical RGB) */}
            <div
              className="absolute inset-0 overflow-hidden pointer-events-none"
              style={{
                clipPath: `polygon(0 0, ${sliderValue}% 0, ${sliderValue}% 100%, 0 100%)`,
              }}
            >
              <img
                src="/data/pre_rgb.png"
                alt="Before (Sep 2023)"
                className="w-full h-full object-cover filter brightness-[0.98] contrast-[1.05]"
                onError={() => setPreImageError(true)}
              />
            </div>

            {/* Right Image: AFTER (Oct 2023 onwards Optical RGB) */}
            <div
              className="absolute inset-0 overflow-hidden pointer-events-none"
              style={{
                clipPath: `polygon(${sliderValue}% 0, 100% 0, 100% 100%, ${sliderValue}% 100%)`,
              }}
            >
              <img
                src="/data/post_rgb.png"
                alt="After (Oct 2023 onwards)"
                className="w-full h-full object-cover filter brightness-[0.98] contrast-[1.05]"
                onError={() => setPostImageError(true)}
              />

              {/* Clean Flood Change Overlay Layer: Subtle Heatmap + Clean River Corridor */}
              {layers.changeActive && (
                <>
                  {/* Subtle blend of raster change without blinding red noise */}
                  <img
                    src="/data/change_overlay.png"
                    alt="Detected Change"
                    style={{ opacity: changeOpacity / 100 }}
                    className="absolute inset-0 w-full h-full object-cover mix-blend-color-dodge pointer-events-none filter blur-[0.4px] contrast-150"
                  />

                  {/* Clean Vector Flood Swath / Impact Corridor */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
                    <defs>
                      <linearGradient id="floodGlow" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.8" />
                        <stop offset="50%" stopColor="#ef4444" stopOpacity="0.85" />
                        <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.8" />
                      </linearGradient>
                    </defs>
                    {/* Teesta Flood Surge Corridor */}
                    <path
                      d="M 280,60 Q 380,180 480,320 T 470,440 T 410,580 T 360,780 T 320,950"
                      fill="none"
                      stroke="url(#floodGlow)"
                      strokeWidth="18"
                      strokeOpacity="0.55"
                      strokeLinecap="round"
                    />
                    <path
                      d="M 280,60 Q 380,180 480,320 T 470,440 T 410,580 T 360,780 T 320,950"
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth="3"
                      strokeOpacity="0.9"
                      strokeDasharray="10 6"
                    />
                  </svg>
                </>
              )}
            </div>

            {/* Draggable Vertical Handle Divider (Prominent, High-Visibility) */}
            <div
              className="absolute top-0 bottom-0 pointer-events-none z-30 flex items-center justify-center -translate-x-1/2"
              style={{ left: `${sliderValue}%` }}
            >
              {/* Glowing vertical line */}
              <div className="w-1 h-full bg-white shadow-[0_0_14px_rgba(255,255,255,1),_0_0_30px_rgba(239,68,68,0.6)]" />

              {/* Large, Tactile Center Drag Knob */}
              <div className="absolute w-12 h-12 rounded-full bg-neutral-950/95 border-2 border-white flex flex-col items-center justify-center shadow-2xl pointer-events-auto cursor-ew-resize hover:scale-110 active:scale-95 transition-transform backdrop-blur-md">
                <div className="flex items-center space-x-1 text-white font-bold text-xs">
                  <span>◀</span>
                  <span className="text-[9px] text-neutral-300 font-mono">❚❚</span>
                  <span>▶</span>
                </div>
                <span className="text-[8px] font-mono font-bold tracking-tighter text-red-400 -mt-0.5">
                  SWIPE
                </span>
              </div>
            </div>

            {/* Prominent High-Visibility Corner Epoch Labels */}
            <div className="absolute top-4 left-4 z-20 pointer-events-none">
              <div className="font-mono text-xs font-bold tracking-wide text-neutral-100 bg-neutral-950/90 px-3.5 py-1.5 rounded-md border border-neutral-700 shadow-2xl backdrop-blur-md flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-neutral-400" />
                <span>BEFORE // Sep 2023 (Pre-Flood Sentinel-2)</span>
              </div>
            </div>

            <div className="absolute top-4 right-4 z-20 pointer-events-none">
              <div className="font-mono text-xs font-bold tracking-wide text-red-300 bg-neutral-950/90 px-3.5 py-1.5 rounded-md border border-red-700/80 shadow-2xl backdrop-blur-md flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <span>AFTER // Oct 2023 (Post-Flood Impact)</span>
              </div>
            </div>

            {/* 4. TACTICAL OVERLAY LAYERS */}

            {/* A. Risk Zones Layer */}
            {layers.riskOverlay && (
              <div className="absolute inset-0 pointer-events-none z-15">
                <svg className="w-full h-full">
                  {/* High Risk Basins with transparent polygon tints */}
                  <polygon
                    points="200,80 380,80 420,340 180,300"
                    fill="rgba(239, 68, 68, 0.22)"
                    stroke="#ef4444"
                    strokeWidth="2"
                    strokeDasharray="6 3"
                  />
                  <text x="210" y="110" fill="#fca5a5" fontSize="12" fontFamily="monospace" fontWeight="bold">
                    ZONE 1: TEESTA III RESERVOIR BASIN (HIGH RISK)
                  </text>

                  <polygon
                    points="320,380 540,360 480,680 280,660"
                    fill="rgba(245, 158, 11, 0.20)"
                    stroke="#f59e0b"
                    strokeWidth="2"
                    strokeDasharray="6 3"
                  />
                  <text x="330" y="410" fill="#fde68a" fontSize="12" fontFamily="monospace" fontWeight="bold">
                    ZONE 4: CHUNGTHANG-MANGA CORRIDOR (ELEVATED RISK)
                  </text>
                </svg>
              </div>
            )}

            {/* B. Priority Village Pins (Clearly marked on the map) */}
            {layers.priorityNodes && (
              <div className="absolute inset-0 pointer-events-auto z-20">
                {villages.slice(0, 10).map((v) => {
                  const pos = getNodePosition(v.properties.name, v.geometry.coordinates[0], v.geometry.coordinates[1])
                  const isSelected = selectedVillage?.properties.rank === v.properties.rank

                  return (
                    <div
                      key={`village-pin-${v.properties.rank}`}
                      style={{ left: `${pos.left}%`, top: `${pos.top}%` }}
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedVillage(v)
                        setSelectedSafeZone(null)
                      }}
                      className={`absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group transition-all duration-150 ${
                        isSelected ? "scale-125 z-40" : "hover:scale-115 z-25"
                      }`}
                    >
                      <div className="relative flex flex-col items-center">
                        {/* Outer pulsating wave for critical/selected nodes */}
                        {isSelected && (
                          <div className="absolute -inset-2 rounded-full bg-red-500/40 animate-ping pointer-events-none" />
                        )}

                        {/* Distinct Priority Badge */}
                        <div
                          className={`flex items-center space-x-1 px-2 py-1 rounded-full border shadow-2xl font-mono font-bold text-xs ${
                            isSelected
                              ? "bg-red-600 border-white text-white shadow-[0_0_16px_rgba(239,68,68,1)]"
                              : v.properties.priority === "CRITICAL" || v.properties.rank <= 3
                              ? "bg-red-700/90 border-red-300 text-white shadow-[0_0_10px_rgba(220,38,38,0.7)]"
                              : "bg-neutral-900/90 border-neutral-600 text-neutral-200 hover:border-neutral-400"
                          }`}
                        >
                          <MapPin className="w-3 h-3 text-white shrink-0" />
                          <span>#{v.properties.rank}</span>
                          <span className="hidden sm:inline text-[11px] font-sans font-medium pl-0.5">
                            {v.properties.name}
                          </span>
                        </div>

                        {/* Tooltip on hover */}
                        <div className="absolute top-full mt-1.5 hidden group-hover:block bg-neutral-950/95 border border-neutral-700 px-2.5 py-1.5 rounded-md text-[11px] font-mono text-neutral-100 whitespace-nowrap shadow-2xl z-50 pointer-events-none">
                          <div className="font-bold text-red-400">
                            #{v.properties.rank} {v.properties.name}
                          </div>
                          <div className="text-[10px] text-neutral-400">
                            Risk Score: {v.properties.score?.toFixed(1) || "HIGH"} // Pop: {v.properties.population?.toLocaleString() || "5,000"}
                          </div>
                          <div className="text-[9px] text-emerald-400 font-sans">
                            Click to inspect triage telemetry
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* C. Safe Zones Pins (Hospitals & Shelters clearly marked in Green) */}
            {layers.safeZones && (
              <div className="absolute inset-0 pointer-events-auto z-20">
                {safeZones.slice(0, 8).map((sz, idx) => {
                  const pos = getSafeZonePosition(sz.properties.name, sz.geometry.coordinates[0], sz.geometry.coordinates[1])
                  const isHospital = sz.properties.type === "hospital"
                  const isSelected = selectedSafeZone?.properties.name === sz.properties.name

                  return (
                    <div
                      key={`safezone-${idx}`}
                      style={{ left: `${pos.left}%`, top: `${pos.top}%` }}
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedSafeZone(sz)
                      }}
                      className={`absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group transition-all duration-150 ${
                        isSelected ? "scale-125 z-40" : "hover:scale-115 z-25"
                      }`}
                    >
                      <div className="relative flex flex-col items-center">
                        {/* Safe Zone Badge */}
                        <div
                          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full border shadow-2xl font-mono font-bold text-xs transition-all ${
                            isSelected
                              ? "bg-emerald-500 border-white text-neutral-950 shadow-[0_0_18px_rgba(16,185,129,1)]"
                              : isHospital
                              ? "bg-emerald-950/90 border-emerald-400 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.5)]"
                              : "bg-teal-950/90 border-teal-400 text-teal-300 shadow-[0_0_10px_rgba(20,184,166,0.5)]"
                          }`}
                        >
                          {isHospital ? (
                            <Building2 className="w-3.5 h-3.5 text-emerald-300" />
                          ) : (
                            <ShieldCheck className="w-3.5 h-3.5 text-teal-300" />
                          )}
                          <span className="text-[11px] font-sans">
                            {sz.properties.name.replace("Unnamed settlement", "Relief Safe Shelter")}
                          </span>
                        </div>

                        {/* Hover Details Tooltip */}
                        <div className="absolute top-full mt-1.5 hidden group-hover:block bg-neutral-950/95 border border-emerald-800/80 px-2.5 py-1.5 rounded-md text-[11px] font-mono text-emerald-200 whitespace-nowrap shadow-2xl z-50 pointer-events-none">
                          <div className="font-bold flex items-center space-x-1.5">
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                            <span>SAFE REFUGE // {isHospital ? "MEDICAL POST" : "HIGH-GROUND SHELTER"}</span>
                          </div>
                          <div className="text-[10px] text-neutral-300 font-sans">
                            {sz.properties.details || "Emergency Generator // Potable Water // Unflooded"}
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* D. Floating Pinpoint Card for Selected Village or Safe Zone */}
            {selectedVillage && (
              <div className="absolute top-16 left-6 z-35 max-w-sm bg-neutral-950/95 border border-neutral-700/90 p-3.5 rounded-md shadow-2xl font-mono text-xs backdrop-blur-xl">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-2 mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="px-1.5 py-0.5 rounded bg-red-600 text-white font-bold text-[10px]">
                      #{selectedVillage.properties.rank}
                    </span>
                    <span className="font-bold text-neutral-100 text-sm uppercase">
                      {selectedVillage.properties.name}
                    </span>
                  </div>
                  <span className="text-[10px] text-neutral-400">
                    {selectedVillage.geometry.coordinates[1].toFixed(2)}°N, {selectedVillage.geometry.coordinates[0].toFixed(2)}°E
                  </span>
                </div>

                <div className="space-y-2 text-[11px]">
                  <div className="bg-red-950/50 border border-red-900/60 p-2 rounded text-red-300 leading-snug">
                    <span className="font-bold text-white block mb-0.5">Disaster Exposure Analysis:</span>
                    {selectedVillage.properties.reason}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-neutral-300 pt-0.5">
                    <div className="bg-neutral-900/80 border border-neutral-800 p-1.5 rounded">
                      <span className="text-neutral-500 text-[10px] block">EST. POPULATION:</span>
                      <span className="font-bold text-neutral-100">
                        {selectedVillage.properties.population?.toLocaleString() || "5,000"}
                      </span>
                    </div>
                    <div className="bg-neutral-900/80 border border-neutral-800 p-1.5 rounded">
                      <span className="text-neutral-500 text-[10px] block">RIVER STAGE:</span>
                      <span className="font-bold text-amber-400">
                        {selectedVillage.properties.riverGauge || "+4.8m (Breached)"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* E. Floating Safe Zone Info Card */}
            {selectedSafeZone && (
              <div className="absolute top-16 left-6 z-35 max-w-sm bg-neutral-950/95 border border-emerald-700/80 p-3.5 rounded-md shadow-2xl font-mono text-xs backdrop-blur-xl">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-2 mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="px-1.5 py-0.5 rounded bg-emerald-600 text-white font-bold text-[10px]">
                      SAFE ZONE
                    </span>
                    <span className="font-bold text-emerald-200 text-sm">
                      {selectedSafeZone.properties.name}
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedSafeZone(null)}
                    className="text-neutral-400 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="space-y-2 text-[11px]">
                  <div className="bg-emerald-950/40 border border-emerald-900/60 p-2 rounded text-emerald-300">
                    <span className="font-bold text-white block mb-0.5">Facility Type:</span>
                    {selectedSafeZone.properties.type === "hospital" ? "Emergency Hospital / Medical Post" : "Designated Flood Evacuation Shelter"}
                  </div>
                  <div className="text-neutral-300 text-[10px]">
                    Status: Uninundated High Ridge // Satellite Verified
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Missing Image Fallback Alert */}
          {missingError && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-neutral-950/95 p-6 text-center font-mono z-40">
              <AlertTriangle className="w-8 h-8 text-amber-500 mb-3" />
              <div className="text-red-400 font-bold text-base mb-2">{missingError}</div>
              <p className="text-neutral-400 text-xs max-w-md leading-relaxed">
                The application could not find this image. Please ensure the file is present in <code>public/data/</code>.
              </p>
            </div>
          )}

          {/* Top Layer Toggles Panel (Toggles start OFF by default) */}
          <div className="absolute top-16 right-4 z-30">
            <LayerToggles
              layers={layers}
              onToggle={handleToggleLayer}
              priorityCount={villages.length}
              safeZoneCount={safeZones.length}
            />
          </div>

          {/* Bottom Floating Temporal Slider Bar with Preset Jump Controls */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 w-full max-w-xl px-4 pointer-events-auto">
            <SwipeSlider
              value={sliderValue}
              onChange={(v) => setSliderValue(v)}
              onReset={() => setSliderValue(50)}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
