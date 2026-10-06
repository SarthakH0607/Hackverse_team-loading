import React from "react"
import { Link } from "react-router-dom"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Compass,
  ExternalLink,
  Eye,
  FileText,
  Flame,
  Globe,
  Layers,
  Lock,
  MapPin,
  Maximize2,
  Navigation,
  Radio,
  Share2,
  Shield,
  ShieldAlert,
  Smartphone,
  Sparkles,
  Terminal,
  Users,
  WifiOff,
  Zap,
} from "lucide-react"

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#08090d] text-neutral-100 flex flex-col font-sans selection:bg-neutral-800 selection:text-white relative overflow-x-hidden">
      {/* Background ambient lighting and tactical grid */}
      <div className="absolute inset-0 tactical-grid-bg opacity-30 pointer-events-none" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[450px] bg-red-600/10 blur-[140px] pointer-events-none rounded-full" />
      <div className="absolute top-[600px] right-0 w-[500px] h-[500px] bg-emerald-600/5 blur-[160px] pointer-events-none rounded-full" />

      {/* 1. Header Navigation Bar */}
      <header className="relative z-30 border-b border-neutral-800/80 bg-neutral-950/80 backdrop-blur-md px-6 py-4 font-mono">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Brand */}
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded bg-red-600/20 border border-red-500/50 flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform">
              <Radio className="w-5 h-5 text-red-500 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold tracking-wider text-base text-neutral-100">
                  EPICENTER
                </span>
                <span className="px-1.5 py-0.2 rounded bg-neutral-900 border border-neutral-800 text-[10px] text-neutral-400 font-semibold">
                  v2.4
                </span>
              </div>
              <div className="text-[10px] tracking-tight text-neutral-400">
                CRITICAL DISASTER GIS &amp; RAPID RESPONSE
              </div>
            </div>
          </Link>

          {/* Nav Links */}
          <nav className="hidden md:flex items-center space-x-6 text-xs text-neutral-300">
            <Link
              to="/dashboard"
              className="hover:text-white transition-colors flex items-center space-x-1.5"
            >
              <span>Responder Console</span>
            </Link>
            <Link
              to="/citizen"
              className="hover:text-white transition-colors flex items-center space-x-1.5"
            >
              <span>Citizen Mode</span>
            </Link>
            <a
              href="/data/incident_report.html"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white transition-colors flex items-center space-x-1.5 text-neutral-400"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Incident Report</span>
            </a>
          </nav>

          {/* Quick CTA */}
          <div className="flex items-center space-x-3">
            <Link
              to="/citizen"
              className="hidden sm:inline-flex items-center space-x-1.5 px-3 py-1.5 rounded bg-neutral-900 border border-neutral-800 hover:border-neutral-700 text-neutral-300 text-xs transition-colors"
            >
              <Smartphone className="w-3.5 h-3.5 text-amber-400" />
              <span>Citizen App</span>
            </Link>
            <Link
              to="/dashboard"
              className="inline-flex items-center space-x-2 px-4 py-1.5 rounded bg-red-600 hover:bg-red-500 text-white font-bold text-xs transition-all shadow-lg hover:shadow-red-600/30"
            >
              <span>Launch Console</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section className="relative z-20 pt-16 pb-20 px-6 max-w-7xl mx-auto text-center font-mono">
        {/* Status Pill Badge */}
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-neutral-900/90 border border-neutral-800 text-xs text-neutral-300 mb-8 backdrop-blur-sm shadow-inner">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[11px] font-medium tracking-wide">
            LIVE INTEL: SIKKIM TEESTA BASIN DELTA // SENTINEL-1 C-SAR ACTIVE
          </span>
        </div>

        {/* Hero Title */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-5xl mx-auto leading-[1.1] mb-6">
          Cloud-Penetrating Disaster Intelligence &amp;{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-500 via-orange-400 to-amber-300">
            Offline Survival Triage
          </span>
        </h1>

        {/* Hero Subtitle */}
        <p className="text-neutral-400 text-sm sm:text-base max-w-3xl mx-auto leading-relaxed mb-10 font-sans">
          When cloud cover blinds optical satellites and cellular towers collapse,{" "}
          <strong className="text-neutral-200">EPICENTER</strong> fuses synthetic aperture radar (SAR) with terrain digital elevation models (DEM) to compute real-time flood exposure, prioritize village rescue nodes, and guide citizens offline.
        </p>

        {/* Dual Primary Call-to-Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 max-w-lg mx-auto mb-16">
          <Link
            to="/dashboard"
            className="w-full sm:w-auto flex-1 inline-flex items-center justify-center space-x-2.5 px-6 py-3.5 rounded bg-red-600 hover:bg-red-500 active:scale-[0.98] text-white font-bold text-sm transition-all shadow-xl shadow-red-600/20 border border-red-500"
          >
            <Radio className="w-4 h-4 animate-pulse" />
            <span>ENTER RESPONDER CONSOLE</span>
            <ArrowRight className="w-4 h-4" />
          </Link>

          <Link
            to="/citizen"
            className="w-full sm:w-auto flex-1 inline-flex items-center justify-center space-x-2.5 px-6 py-3.5 rounded bg-neutral-900 hover:bg-neutral-850 active:scale-[0.98] text-neutral-100 font-bold text-sm transition-all border border-neutral-700 shadow-lg"
          >
            <Smartphone className="w-4 h-4 text-emerald-400" />
            <span>CITIZEN OFFLINE MODE</span>
          </Link>
        </div>

        {/* Real-time Telemetry Strip Preview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-4xl mx-auto bg-neutral-950/80 border border-neutral-800/80 rounded-md p-4 text-left backdrop-blur-md shadow-2xl">
          <div className="p-2 border-r border-neutral-850">
            <span className="text-[10px] text-neutral-400 block uppercase tracking-wider">
              AFFECTED AREA
            </span>
            <div className="text-xl sm:text-2xl font-bold text-white mt-0.5">
              418.6 <span className="text-xs text-neutral-400 font-normal">km²</span>
            </div>
            <span className="text-[10px] text-red-400 font-medium">
              +54.2 km² in last 6h
            </span>
          </div>

          <div className="p-2 border-r border-neutral-850">
            <span className="text-[10px] text-neutral-400 block uppercase tracking-wider">
              CIVILIANS AT RISK
            </span>
            <div className="text-xl sm:text-2xl font-bold text-white mt-0.5">
              24,858
            </div>
            <span className="text-[10px] text-neutral-400">
              Across Teesta Basin
            </span>
          </div>

          <div className="p-2 border-r border-neutral-850">
            <span className="text-[10px] text-neutral-400 block uppercase tracking-wider">
              RANKED VILLAGE NODES
            </span>
            <div className="text-xl sm:text-2xl font-bold text-red-400 mt-0.5">
              70+ Nodes
            </div>
            <span className="text-[10px] text-amber-400">
              Chungthang &amp; Lachung #1
            </span>
          </div>

          <div className="p-2">
            <span className="text-[10px] text-neutral-400 block uppercase tracking-wider">
              INDEXED SAFE ZONES
            </span>
            <div className="text-xl sm:text-2xl font-bold text-emerald-400 mt-0.5">
              103 Zones
            </div>
            <span className="text-[10px] text-emerald-400">
              Hospitals, Shelters, Water
            </span>
          </div>
        </div>
      </section>

      {/* 3. The Dual Ecosystem Feature Cards */}
      <section className="relative z-20 py-16 px-6 max-w-7xl mx-auto w-full font-mono">
        <div className="text-center mb-12">
          <span className="text-xs uppercase tracking-widest text-neutral-400 font-bold">
            ARCHITECTED FOR CRISIS
          </span>
          <h2 className="text-2xl sm:text-4xl font-extrabold text-white mt-2">
            Two Specialized Interfaces, One Unified Mission
          </h2>
          <p className="text-xs sm:text-sm text-neutral-400 mt-2 font-sans max-w-2xl mx-auto">
            High-density tactical situational awareness for command centers, alongside an offline-first resilient companion for citizens in the disaster zone.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Card 1: Responder Console */}
          <div className="bg-gradient-to-b from-neutral-900/90 to-neutral-950 border border-neutral-800 rounded-lg p-6 sm:p-8 flex flex-col justify-between shadow-2xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-48 h-48 bg-red-600/10 rounded-full blur-3xl pointer-events-none group-hover:bg-red-600/20 transition-all" />
            
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="px-2.5 py-1 rounded bg-red-950/80 border border-red-800/80 text-red-400 text-xs font-bold flex items-center space-x-1.5">
                  <Radio className="w-3.5 h-3.5" />
                  <span>DESKTOP COMMAND</span>
                </span>
                <span className="text-xs text-neutral-400">MapLibre GIS • Multi-Layer</span>
              </div>

              <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">
                Tactical Responder Console
              </h3>
              <p className="text-neutral-400 text-xs sm:text-sm font-sans mb-6 leading-relaxed">
                Empowers emergency coordinators, army NDRF personnel, and medical triage leads with algorithmic priority matrices.
              </p>

              {/* Feature List */}
              <ul className="space-y-2.5 text-xs text-neutral-300 font-mono mb-8">
                <li className="flex items-start space-x-2">
                  <span className="text-red-400 mt-0.5">▶</span>
                  <span><strong>SAR Water Change Detection</strong>: Sentinel-1 dual-pol VV radar penetrates thick cloud covers.</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-red-400 mt-0.5">▶</span>
                  <span><strong>Algorithmic Village Ranking</strong>: Exposure scores based on road severance, isolation, and vulnerable populations.</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-red-400 mt-0.5">▶</span>
                  <span><strong>Dual-Split Temporal Swipe</strong>: Compare pre-flood baseline imagery directly against post-disaster flood surge.</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-red-400 mt-0.5">▶</span>
                  <span><strong>Multi-Sector Operations</strong>: Active monitoring for Sikkim Teesta, ready for Kedarnath Mandakini.</span>
                </li>
              </ul>
            </div>

            <Link
              to="/dashboard"
              className="inline-flex items-center justify-between px-5 py-3 rounded bg-neutral-900 hover:bg-neutral-800 border border-neutral-700 text-white font-bold text-xs transition-colors group-hover:border-red-500/50"
            >
              <span>OPEN RESPONDER CONSOLE</span>
              <ArrowRight className="w-4 h-4 text-red-400 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>

          {/* Card 2: Citizen Mode */}
          <div className="bg-gradient-to-b from-neutral-900/90 to-neutral-950 border border-neutral-800 rounded-lg p-6 sm:p-8 flex flex-col justify-between shadow-2xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-48 h-48 bg-emerald-600/10 rounded-full blur-3xl pointer-events-none group-hover:bg-emerald-600/20 transition-all" />

            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="px-2.5 py-1 rounded bg-emerald-950/80 border border-emerald-800/80 text-emerald-400 text-xs font-bold flex items-center space-x-1.5">
                  <WifiOff className="w-3.5 h-3.5" />
                  <span>MOBILE-FIRST OFFLINE</span>
                </span>
                <span className="text-xs text-neutral-400">Zero Internet Required</span>
              </div>

              <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">
                Citizen Survival &amp; Navigation Mode
              </h3>
              <p className="text-neutral-400 text-xs sm:text-sm font-sans mb-6 leading-relaxed">
                Engineered for trapped civilians and isolated community responders when mobile cellular networks and power grids blackout.
              </p>

              {/* Feature List */}
              <ul className="space-y-2.5 text-xs text-neutral-300 font-mono mb-8">
                <li className="flex items-start space-x-2">
                  <span className="text-emerald-400 mt-0.5">▶</span>
                  <span><strong>Hardware Dead-Reckoning Compass</strong>: Azimuth bearing needle points directly toward safe relief zones.</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-emerald-400 mt-0.5">▶</span>
                  <span><strong>103 Topographic Safe Points</strong>: Monasteries, schools, and ridge caves verified above flood surge level.</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-emerald-400 mt-0.5">▶</span>
                  <span><strong>Acoustic &amp; BLE Mesh Beacon</strong>: Silently broadcasts distress packets to passing rescue patrols and peers.</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-emerald-400 mt-0.5">▶</span>
                  <span><strong>Emergency Hardware Calling</strong>: 1-tap bypass to dial 112 disaster police and 108 medical ambulances.</span>
                </li>
              </ul>
            </div>

            <Link
              to="/citizen"
              className="inline-flex items-center justify-between px-5 py-3 rounded bg-neutral-900 hover:bg-neutral-800 border border-neutral-700 text-white font-bold text-xs transition-colors group-hover:border-emerald-500/50"
            >
              <span>LAUNCH CITIZEN MODE</span>
              <ArrowRight className="w-4 h-4 text-emerald-400 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </section>

      {/* 4. Technical Architecture Details */}
      <section className="relative z-20 py-12 px-6 max-w-7xl mx-auto w-full font-mono border-t border-neutral-850">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs">
          <div className="p-4 bg-neutral-950 border border-neutral-800 rounded">
            <div className="flex items-center space-x-2 text-neutral-100 font-bold mb-2">
              <Globe className="w-4 h-4 text-blue-400" />
              <span>Sentinel-1 SAR C-Band Radar</span>
            </div>
            <p className="text-neutral-400 leading-relaxed font-sans text-[11px]">
              Active microwave sensor emits 5.405 GHz pulses capable of penetrating nocturnal darkness, monsoon rains, and dense Himalayan cloud cover.
            </p>
          </div>

          <div className="p-4 bg-neutral-950 border border-neutral-800 rounded">
            <div className="flex items-center space-x-2 text-neutral-100 font-bold mb-2">
              <Layers className="w-4 h-4 text-amber-400" />
              <span>SRTM 30m Slope &amp; Buffer Criteria</span>
            </div>
            <p className="text-neutral-400 leading-relaxed font-sans text-[11px]">
              Identifies safe zones with terrain slope &lt;15°, distance to nearest river &gt;200m, and proximity to roads &lt;500m to avoid mudslide funnels.
            </p>
          </div>

          <div className="p-4 bg-neutral-950 border border-neutral-800 rounded">
            <div className="flex items-center space-x-2 text-neutral-100 font-bold mb-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <span>Supabase Cloud + Local GeoJSON Fallback</span>
            </div>
            <p className="text-neutral-400 leading-relaxed font-sans text-[11px]">
              Hybrid storage architecture synchronizes live field telemetry via Supabase when online, failing over to local geo-cached bundles offline.
            </p>
          </div>
        </div>
      </section>

      {/* 5. Footer */}
      <footer className="relative z-20 border-t border-neutral-850 bg-neutral-950 py-6 px-6 font-mono text-[11px] text-neutral-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-neutral-300 font-bold">EPICENTER DISASTER ENGINE</span>
            <span className="text-neutral-600">//</span>
            <span>HACKVERSE TEAM LOADING</span>
          </div>

          <div className="flex items-center space-x-4">
            <a
              href="/data/incident_report.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-neutral-400 hover:text-white transition-colors"
            >
              Incident Report
            </a>
            <Link to="/dashboard" className="text-neutral-400 hover:text-white transition-colors">
              Responder
            </Link>
            <Link to="/citizen" className="text-neutral-400 hover:text-white transition-colors">
              Citizen
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
