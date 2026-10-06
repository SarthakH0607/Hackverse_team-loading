import React, { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import {
  getSafeZones,
  SafeZoneFeature,
  SafeZoneType,
} from "@/lib/data"
import { CompassArrow } from "@/components/CompassArrow"
import { SafeZoneChips } from "@/components/SafeZoneChips"
import {
  formatBearing,
  formatCoordinates,
  calculateDistance,
  calculateBearing,
  calculateWalkingTimeMinutes,
} from "@/lib/geo"
import {
  AlertTriangle,
  ArrowRight,
  BatteryCharging,
  CheckCircle2,
  ChevronRight,
  Compass,
  Globe,
  Lock,
  Monitor,
  PhoneCall,
  Radio,
  RefreshCw,
  Share2,
  Shield,
  ShieldAlert,
  Smartphone,
  User,
  Volume2,
  WifiOff,
  Zap,
} from "lucide-react"

type CitizenTab = "sos" | "compass" | "queue"

export const CitizenMode: React.FC = () => {
  const [activeTab, setActiveTab] = useState<CitizenTab>("sos")
  const [safeZones, setSafeZones] = useState<SafeZoneFeature[]>([])
  const [selectedZone, setSelectedZone] = useState<SafeZoneFeature | null>(null)
  const [chipFilter, setChipFilter] = useState<SafeZoneType | "all">("all")
  const [isBeaconActive, setIsBeaconActive] = useState<boolean>(false)
  const [safeCheckInStatus, setSafeCheckInStatus] = useState<boolean>(false)
  const [gpsRefreshing, setGpsRefreshing] = useState<boolean>(false)

  // Citizen mock GPS location (Dikchu / Teesta valley foothills)
  const userLat = 27.4812
  const userLon = 88.5284

  useEffect(() => {
    getSafeZones("sikkim").then((res) => {
      setSafeZones(res.data.features || [])
      if (res.data.features && res.data.features.length > 0) {
        setSelectedZone(res.data.features[0])
      }
    })
  }, [])

  // Trigger Distress Beacon
  const handleTriggerSOS = () => {
    setIsBeaconActive(true)
    setActiveTab("queue")
  }

  // Check in as safe
  const handleCheckInSafe = () => {
    setSafeCheckInStatus(true)
    setTimeout(() => {
      alert("Status updated to SAFE on local mesh and peer Bluetooth cache.")
    }, 150)
  }

  // Cancel distress
  const handleCancelDistress = () => {
    setIsBeaconActive(false)
    setActiveTab("sos")
  }

  // Refresh GPS
  const handleRefreshGps = () => {
    setGpsRefreshing(true)
    setTimeout(() => {
      setGpsRefreshing(false)
    }, 800)
  }

  // Filtered zones for list
  const filteredSafeZones = safeZones.filter((zone) => {
    if (chipFilter === "all") return true
    return zone.properties.type === chipFilter
  })

  // Primary destination
  const primaryZone = selectedZone || safeZones[0]

  // Calculated distance & bearing
  const destLat = primaryZone?.properties.lat ?? 27.4812
  const destLon = primaryZone?.properties.lon ?? 88.5284
  const calculatedDist = calculateDistance(userLat, userLon, destLat, destLon)
  const calculatedBearingDeg = calculateBearing(userLat, userLon, destLat, destLon)
  const bearingString = formatBearing(calculatedBearingDeg || 38)
  const walkMins = calculateWalkingTimeMinutes(calculatedDist || 1.4)

  return (
    <div className="min-h-screen bg-[#08090d] text-neutral-100 flex justify-center font-sans">
      {/* Mobile-First Shell (Centered on desktop with subtle max-w-md constraint) */}
      <div className="w-full max-w-md bg-[#0a0c12] border-x border-neutral-800/80 min-h-screen flex flex-col relative pb-20 shadow-2xl">
        {/* Top App Header */}
        <header className="bg-neutral-950/95 border-b border-neutral-800/90 px-4 py-2.5 flex items-center justify-between sticky top-0 z-40 backdrop-blur-md font-mono">
          <div className="flex items-center space-x-2">
            <Radio className="w-4 h-4 text-red-500 animate-pulse" />
            <span className="font-extrabold tracking-wider text-sm text-neutral-100">
              EPICENTER
            </span>
            <div className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-amber-950/80 border border-amber-800/80 text-[10px] text-amber-400 font-bold">
              <WifiOff className="w-2.5 h-2.5" />
              <span>OFFLINE</span>
            </div>
          </div>

          <div className="flex items-center space-x-2.5 text-xs text-neutral-400">
            {/* Desktop Console Switcher */}
            <Link
              to="/"
              className="hidden xs:flex items-center space-x-1 px-2 py-1 rounded bg-neutral-900 border border-neutral-800 hover:border-neutral-700 text-neutral-300 text-[10px]"
              title="Open Desktop Console"
            >
              <Monitor className="w-3 h-3 text-neutral-400" />
              <span>Console</span>
            </Link>

            {/* Language */}
            <button className="flex items-center space-x-1 px-1.5 py-1 text-[11px] text-neutral-300">
              <Globe className="w-3 h-3 text-neutral-400" />
              <span>EN</span>
            </button>

            {/* User Profile */}
            <div className="w-6 h-6 rounded-full bg-neutral-800 border border-neutral-700 flex items-center justify-center">
              <User className="w-3 h-3 text-neutral-400" />
            </div>
          </div>
        </header>

        {/* Content Views */}
        <div className="flex-1 overflow-y-auto">
          {/* TAB 1: SOS / SAFE MODE */}
          {activeTab === "sos" && (
            <div className="p-4 space-y-4 font-mono">
              {/* Offline Banner */}
              <div className="bg-neutral-900/80 border border-neutral-800 rounded-sm p-2.5 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2 text-neutral-300">
                  <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                  <span className="text-[11px]">
                    OFFLINE MODE ACTIVE • Works 100% without internet
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded bg-neutral-800 text-[10px] text-neutral-200 border border-neutral-700 font-bold flex items-center space-x-1">
                  <Share2 className="w-2.5 h-2.5 text-emerald-400 mr-1" />
                  MESH ON
                </span>
              </div>

              {/* Hardware GPS Status Card */}
              <div className="bg-neutral-950 border border-neutral-800/90 rounded-sm p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-bold flex items-center space-x-1.5">
                    <Lock className="w-3 h-3 text-neutral-400" />
                    <span>GPS LOCKED (HARDWARE)</span>
                  </span>
                  <button
                    onClick={handleRefreshGps}
                    className="flex items-center space-x-1 text-[10px] text-neutral-400 hover:text-neutral-200 transition-colors"
                  >
                    <RefreshCw
                      className={`w-3 h-3 ${gpsRefreshing ? "animate-spin text-neutral-200" : ""}`}
                    />
                    <span>Retry</span>
                  </button>
                </div>
                <div className="text-neutral-100 font-bold text-sm tracking-wide">
                  {formatCoordinates(userLat, userLon)}
                </div>
              </div>

              {/* Acoustic & Radio Beacon Notice */}
              <div className="bg-neutral-900/50 border border-neutral-800/80 rounded-sm p-2.5 text-[11px] text-neutral-400 flex items-start space-x-2">
                <Volume2 className="w-4 h-4 text-amber-500 shrink-0 mt-0.5 animate-pulse" />
                <p className="leading-snug">
                  Keep this screen open. Your phone is silently broadcasting an emergency acoustic &amp; radio beacon.
                </p>
              </div>

              {/* BIG ACTION BUTTONS */}
              <div className="space-y-3 pt-1">
                {/* 1. SOS - I NEED HELP BUTTON */}
                <button
                  onClick={handleTriggerSOS}
                  className="w-full bg-red-600 hover:bg-red-500 active:scale-[0.98] text-white p-4 rounded-md shadow-xl transition-all flex items-center justify-between group border border-red-500 text-left"
                >
                  <div className="flex items-center space-x-3.5">
                    <div className="w-10 h-10 rounded-sm bg-red-700/80 border border-red-400/50 flex items-center justify-center font-black text-sm tracking-widest shadow-inner">
                      SOS
                    </div>
                    <div>
                      <div className="font-black text-lg tracking-wide leading-tight">
                        I NEED HELP
                      </div>
                      <div className="text-xs text-red-100 font-mono tracking-tight opacity-90">
                        BROADCAST DISTRESS NOW
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="w-6 h-6 text-white group-hover:translate-x-1 transition-transform" />
                </button>

                {/* 2. I AM SAFE - CHECK IN BUTTON */}
                <button
                  onClick={handleCheckInSafe}
                  className={`w-full p-3.5 rounded-md transition-all flex items-center justify-between border text-left ${
                    safeCheckInStatus
                      ? "bg-emerald-950/60 border-emerald-500 text-emerald-300"
                      : "bg-neutral-900/90 hover:bg-neutral-800 border-neutral-800 text-neutral-200"
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <CheckCircle2
                      className={`w-5 h-5 ${
                        safeCheckInStatus ? "text-emerald-400" : "text-neutral-400"
                      }`}
                    />
                    <div>
                      <div className="font-bold text-sm">
                        {safeCheckInStatus ? "RECORDED AS SAFE" : "I AM SAFE — Check In"}
                      </div>
                      <div className="text-[11px] text-neutral-400">
                        Record status on local mesh
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-neutral-400" />
                </button>
              </div>

              {/* Nearest Safe Zone Card */}
              <div className="bg-neutral-950 border border-neutral-800/90 rounded-sm p-3.5 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-bold">
                    NEAREST SAFE ZONE
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[9px] bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                    OPEN NOW
                  </span>
                </div>

                <div>
                  <div className="flex items-center space-x-2">
                    <Shield className="w-4 h-4 text-emerald-400 shrink-0" />
                    <h3 className="text-neutral-100 font-bold text-sm">
                      {primaryZone?.properties.name || "St. Xavier Relief Camp"}
                    </h3>
                  </div>
                  <p className="text-[11px] text-neutral-400 mt-0.5 ml-6">
                    {primaryZone?.properties.subtitle || "Community Hall • High Ground Grounding"}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs py-1 ml-6">
                  <div>
                    <span className="text-[10px] text-neutral-400 block">DISTANCE</span>
                    <span className="text-neutral-100 font-bold text-sm">
                      {primaryZone?.properties.distanceKm || 1.4} km
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-neutral-400 block">ON FOOT</span>
                    <span className="text-neutral-100 font-bold text-sm">
                      ~{primaryZone?.properties.estWalkMinutes || 18} mins
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => setActiveTab("compass")}
                  className="w-full bg-neutral-900 hover:bg-neutral-850 active:bg-neutral-800 border border-neutral-700 py-2.5 px-3 rounded text-xs font-bold text-neutral-200 flex items-center justify-center space-x-2 transition-colors"
                >
                  <Compass className="w-4 h-4 text-neutral-300" />
                  <span>Open Offline Compass Guide</span>
                </button>
              </div>

              {/* Direct Hardware Calling */}
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between text-[10px] text-neutral-400 font-bold uppercase tracking-wider">
                  <span>DIRECT HARDWARE CALLING</span>
                  <span>GSM / TOWER BYPASS</span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <a
                    href="tel:112"
                    className="bg-neutral-900/90 hover:bg-neutral-800 border border-neutral-800 p-2.5 rounded text-center flex flex-col items-center justify-center space-y-1 transition-colors"
                  >
                    <div className="flex items-center space-x-1.5 text-neutral-100 font-bold text-xs">
                      <PhoneCall className="w-3.5 h-3.5 text-red-500" />
                      <span>112</span>
                    </div>
                    <span className="text-[9px] text-neutral-400">POLICE / DISASTER</span>
                  </a>

                  <a
                    href="tel:108"
                    className="bg-neutral-900/90 hover:bg-neutral-800 border border-neutral-800 p-2.5 rounded text-center flex flex-col items-center justify-center space-y-1 transition-colors"
                  >
                    <div className="flex items-center space-x-1.5 text-neutral-100 font-bold text-xs">
                      <PhoneCall className="w-3.5 h-3.5 text-emerald-400" />
                      <span>108</span>
                    </div>
                    <span className="text-[9px] text-neutral-400">AMBULANCE</span>
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: COMPASS GUIDE MODE */}
          {activeTab === "compass" && (
            <div className="p-4 space-y-4 font-mono">
              {/* Compass Status Banner */}
              <div className="bg-neutral-900/80 border border-neutral-800 rounded-sm p-2 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2 text-neutral-300">
                  <Compass className="w-3.5 h-3.5 text-neutral-400" />
                  <span className="text-[11px]">
                    Offline mode active • Local compass
                  </span>
                </div>
                <span className="px-1.5 py-0.5 rounded bg-neutral-800 text-[10px] text-amber-400 border border-neutral-700 font-semibold">
                  CACHED FIX
                </span>
              </div>

              {/* Dead-Reckoning Contour Note */}
              <div className="bg-neutral-950 border border-neutral-850 p-2.5 rounded-sm text-[11px] text-neutral-400 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-neutral-300 font-semibold">
                    Searching for satellite fix...
                  </span>
                  <span className="text-[10px] text-neutral-400">TTL 4m</span>
                </div>
                <p className="text-[10px] leading-snug">
                  Operating via cached magnetometer and terrain dead-reckoning contour.
                </p>
                <div className="text-[10px] text-neutral-400 hover:text-neutral-200 cursor-pointer pt-1 flex items-center space-x-1">
                  <RefreshCw className="w-2.5 h-2.5" />
                  <span>Location drifting? Tap to recalibrate sensor</span>
                </div>
              </div>

              {/* Compass Arrow & Dial */}
              <div className="bg-neutral-950 border border-neutral-800/90 rounded-sm p-3">
                <CompassArrow
                  bearingDegrees={calculatedBearingDeg || 38}
                  bearingLabel={bearingString}
                  altitudeContour={primaryZone?.properties.elevationDelta || "+184m HIGH GROUND"}
                  distanceKm={primaryZone?.properties.distanceKm || 1.4}
                  walkMinutes={primaryZone?.properties.estWalkMinutes || 20}
                />
              </div>

              {/* Primary Destination Detail Card */}
              <div className="bg-neutral-950 border border-neutral-800/90 rounded-sm p-3 space-y-2">
                <div className="flex items-start space-x-2">
                  <Shield className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div className="min-w-0">
                    <span className="text-[10px] text-neutral-400 block uppercase font-bold">
                      PRIMARY DESTINATION
                    </span>
                    <h3 className="text-neutral-100 font-bold text-sm truncate">
                      {primaryZone?.properties.name}
                    </h3>
                  </div>
                </div>

                <p className="text-[11px] text-neutral-400 leading-tight">
                  {primaryZone?.properties.details ||
                    "Type: Community Haven • Verified above flood zone contour (+24m buffer)."}
                </p>

                <div className="flex items-center space-x-3 text-[10px] pt-1 border-t border-neutral-900">
                  <span className="text-emerald-400 flex items-center space-x-1">
                    <CheckCircle2 className="w-3 h-3 mr-0.5" />
                    <span>Generator: {primaryZone?.properties.generator || "ACTIVE"}</span>
                  </span>
                  <span className="text-neutral-400">|</span>
                  <span className="text-blue-400">
                    Potable Spring: {primaryZone?.properties.potableSpring || "YES"}
                  </span>
                </div>
              </div>

              {/* Zone Priority Category Filter Chips */}
              <SafeZoneChips
                selectedType={chipFilter}
                onSelectType={(type) => setChipFilter(type)}
              />

              {/* Secondary Escape Zones */}
              <div className="space-y-2">
                <div className="text-[10px] text-neutral-400 uppercase tracking-wider font-bold flex items-center justify-between">
                  <span>SECONDARY ESCAPE ZONES ({filteredSafeZones.length} AVAILABLE)</span>
                </div>

                <div className="space-y-1.5">
                  {filteredSafeZones
                    .filter((z) => z.properties.name !== primaryZone?.properties.name)
                    .slice(0, 3)
                    .map((zone) => (
                      <div
                        key={zone.properties.name}
                        onClick={() => setSelectedZone(zone)}
                        className="bg-neutral-900/70 hover:bg-neutral-900 border border-neutral-800 p-2.5 rounded cursor-pointer transition-colors flex items-center justify-between"
                      >
                        <div className="min-w-0">
                          <div className="text-xs font-bold text-neutral-100 truncate">
                            {zone.properties.name}
                          </div>
                          <div className="text-[10px] text-neutral-400 truncate">
                            {zone.properties.estWalkMinutes || 45} min walk • {zone.properties.subtitle}
                          </div>
                        </div>

                        <div className="text-right shrink-0 ml-2">
                          <div className="text-xs font-bold text-neutral-200">
                            {zone.properties.distanceKm || 3.2} km
                          </div>
                          <div className="text-[9px] text-neutral-400">
                            BEARING {zone.properties.bearing || "062°"}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Walking Guidance Action Button */}
              <button
                onClick={() => alert(`Starting ridge navigation guidance towards ${primaryZone?.properties.name}`)}
                className="w-full bg-neutral-100 hover:bg-white text-neutral-950 font-bold py-3 rounded text-xs flex items-center justify-center space-x-2 transition-colors shadow-lg"
              >
                <span>🚶 START WALKING GUIDANCE (RIDGE PATH)</span>
              </button>
            </div>
          )}

          {/* TAB 3: MEDICAL TRIAGE INTAKE / OFFLINE QUEUE */}
          {activeTab === "queue" && (
            <div className="p-4 space-y-4 font-mono">
              {/* Beacon Active Header */}
              <div className="bg-neutral-950 border border-neutral-800/90 rounded-sm p-4 text-center space-y-3">
                <div className="relative inline-flex items-center justify-center">
                  <div className="w-16 h-16 rounded-full bg-red-600/20 border border-red-500/50 flex items-center justify-center">
                    <Radio className="w-8 h-8 text-red-500 animate-pulse" />
                  </div>
                  <div className="absolute -inset-1 rounded-full border border-red-500/30 animate-ping pointer-events-none" />
                </div>

                <div className="space-y-1">
                  <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded bg-red-950/60 border border-red-900/80 text-red-400 text-[10px] font-bold">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                    <span>BEACON ACTIVE • OFFLINE QUEUE</span>
                  </div>
                  <h2 className="text-base font-extrabold text-neutral-100 leading-snug">
                    Help request saved. It will send when you're back online.
                  </h2>
                  <p className="text-[11px] text-neutral-400">
                    Queued 1 report • Stored locally in phone memory
                  </p>
                </div>
              </div>

              {/* Mesh Dispatch Active Notice */}
              <div className="bg-neutral-900/60 border border-neutral-800 rounded-sm p-3 text-[11px] text-neutral-300 flex items-start space-x-2.5">
                <Share2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="font-bold text-neutral-100">
                    Mesh Dispatch Active
                  </div>
                  <p className="text-neutral-400 text-[10px] leading-relaxed">
                    Your phone is pulsing this beacon via low-frequency Bluetooth &amp; LoRa mesh to nearby responders and rescue units.
                  </p>
                </div>
              </div>

              {/* Diagnostic Telemetry */}
              <div className="bg-neutral-950 border border-neutral-800/90 rounded-sm p-3.5 space-y-2 text-xs">
                <div className="flex items-center justify-between border-b border-neutral-900 pb-2">
                  <span className="text-[10px] text-neutral-400 uppercase font-bold tracking-wider">
                    DIAGNOSTIC TELEMETRY
                  </span>
                  <span className="text-[10px] text-emerald-400 flex items-center space-x-1">
                    <Lock className="w-2.5 h-2.5" />
                    <span>OFFLINE LOCK</span>
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-[9px] text-neutral-400 block">REPORT ID:</span>
                    <span className="text-neutral-200 font-bold">#SOS-84928</span>
                  </div>
                  <div>
                    <span className="text-[9px] text-neutral-400 block">LOGGED TIMESTAMP:</span>
                    <span className="text-neutral-200">Just now</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-neutral-900">
                  <span className="text-[9px] text-neutral-400 block">GPS COORDINATES (CACHED):</span>
                  <div className="text-neutral-100 font-bold flex items-center space-x-1 text-[11px]">
                    <span>{formatCoordinates(userLat, userLon)} (±4m accuracy)</span>
                    <Lock className="w-3 h-3 text-neutral-400" />
                  </div>
                </div>

                <div className="text-[10px] text-neutral-400 flex items-center space-x-1.5 pt-1">
                  <Zap className="w-3 h-3 text-amber-500" />
                  <span>Battery Optimization: Dimming Active</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2 pt-1">
                <button
                  onClick={() => setActiveTab("compass")}
                  className="w-full bg-neutral-100 hover:bg-white text-neutral-950 font-bold py-2.5 px-3 rounded text-xs transition-colors flex items-center justify-center space-x-2"
                >
                  <Compass className="w-4 h-4 text-neutral-900" />
                  <span>View Nearest Safe Zone (1.4 km)</span>
                </button>

                <a
                  href="tel:112"
                  className="w-full bg-neutral-900 hover:bg-neutral-850 border border-neutral-800 text-neutral-200 font-semibold py-2.5 px-3 rounded text-xs transition-colors flex items-center justify-center space-x-2"
                >
                  <PhoneCall className="w-4 h-4 text-red-400" />
                  <span>Call 112 directly (No cellular data required)</span>
                </a>

                <button
                  onClick={handleCancelDistress}
                  className="w-full text-neutral-400 hover:text-neutral-200 py-2 text-xs transition-colors text-center"
                >
                  ✔ Cancel request (I'm now safe)
                </button>
              </div>

              {/* Warning note */}
              <div className="text-center text-[10px] text-amber-500/80 pt-2 flex items-center justify-center space-x-1.5">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                <span>Do not restart your phone. Keep battery on.</span>
              </div>
            </div>
          )}
        </div>

        {/* Fixed Bottom Navigation Bar (SOS / SAFE, COMPASS, QUEUE) */}
        <nav className="absolute bottom-0 left-0 right-0 bg-neutral-950/98 border-t border-neutral-800/90 h-16 flex items-center justify-around z-40 font-mono text-[10px]">
          {/* Tab 1: SOS / SAFE */}
          <button
            onClick={() => setActiveTab("sos")}
            className={`flex flex-col items-center justify-center flex-1 h-full transition-colors ${
              activeTab === "sos"
                ? "text-neutral-100 font-bold border-t-2 border-red-500 bg-neutral-900/50"
                : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <ShieldAlert className="w-5 h-5 mb-0.5" />
            <span>SOS / SAFE</span>
          </button>

          {/* Tab 2: COMPASS */}
          <button
            onClick={() => setActiveTab("compass")}
            className={`flex flex-col items-center justify-center flex-1 h-full transition-colors ${
              activeTab === "compass"
                ? "text-neutral-100 font-bold border-t-2 border-white bg-neutral-900/50"
                : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <Compass className="w-5 h-5 mb-0.5" />
            <span>COMPASS</span>
          </button>

          {/* Tab 3: QUEUE */}
          <button
            onClick={() => setActiveTab("queue")}
            className={`flex flex-col items-center justify-center flex-1 h-full transition-colors relative ${
              activeTab === "queue"
                ? "text-neutral-100 font-bold border-t-2 border-amber-500 bg-neutral-900/50"
                : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <Radio className="w-5 h-5 mb-0.5" />
            <span>QUEUE</span>
            {isBeaconActive && (
              <span className="absolute top-2 right-8 w-2 h-2 rounded-full bg-red-500 animate-ping" />
            )}
          </button>
        </nav>
      </div>
    </div>
  )
}
