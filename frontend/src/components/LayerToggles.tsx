import React from "react"
import { Layers, ShieldCheck, MapPin, Waves, AlertTriangle } from "lucide-react"

export interface LayerState {
  changeActive: boolean
  riskOverlay: boolean
  priorityNodes: boolean
  safeZones: boolean
}

interface LayerTogglesProps {
  layers: LayerState
  onToggle: (layer: keyof LayerState) => void
  priorityCount?: number
  safeZoneCount?: number
}

export const LayerToggles: React.FC<LayerTogglesProps> = ({
  layers,
  onToggle,
  priorityCount = 14,
  safeZoneCount = 12,
}) => {
  return (
    <div className="flex flex-wrap items-center gap-2 bg-neutral-950/95 border border-neutral-750/90 p-1.5 rounded-md shadow-2xl backdrop-blur-xl font-mono text-xs">
      <div className="px-2.5 py-1 text-neutral-400 border-r border-neutral-800 hidden sm:flex items-center space-x-2">
        <Layers className="w-3.5 h-3.5 text-neutral-300" />
        <span className="uppercase text-[11px] tracking-wider font-bold text-neutral-200">LAYERS</span>
      </div>

      {/* Priority Nodes */}
      <button
        onClick={() => onToggle("priorityNodes")}
        className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition-all ${
          layers.priorityNodes
            ? "bg-red-600/90 text-white font-bold border border-red-400 shadow-md shadow-red-900/40"
            : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900 border border-transparent"
        }`}
        title="Toggle Village Priority Markers"
      >
        <MapPin className="w-3.5 h-3.5" />
        <span>Priority</span>
        <span className="px-1 py-0.2 rounded bg-neutral-900/80 text-[10px] text-neutral-300">
          {priorityCount}
        </span>
      </button>

      {/* Safe Zones */}
      <button
        onClick={() => onToggle("safeZones")}
        className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition-all ${
          layers.safeZones
            ? "bg-emerald-600/90 text-white font-bold border border-emerald-400 shadow-md shadow-emerald-900/40"
            : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900 border border-transparent"
        }`}
        title="Toggle Hospitals and Safe Shelters"
      >
        <ShieldCheck className="w-3.5 h-3.5" />
        <span>Safe Zones</span>
        <span className="px-1 py-0.2 rounded bg-neutral-900/80 text-[10px] text-neutral-300">
          {safeZoneCount}
        </span>
      </button>

      {/* Change Layer */}
      <button
        onClick={() => onToggle("changeActive")}
        className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition-all ${
          layers.changeActive
            ? "bg-neutral-200 text-neutral-950 font-bold border border-white shadow-md"
            : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900 border border-transparent"
        }`}
        title="Toggle Flood Change Impact Layer"
      >
        <Waves className="w-3.5 h-3.5 text-amber-500" />
        <span>Flood Change</span>
      </button>

      {/* Risk Overlay */}
      <button
        onClick={() => onToggle("riskOverlay")}
        className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition-all ${
          layers.riskOverlay
            ? "bg-amber-500 text-neutral-950 font-bold border border-amber-300 shadow-md"
            : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900 border border-transparent"
        }`}
        title="Toggle High-Risk Flood Basins"
      >
        <AlertTriangle className="w-3.5 h-3.5" />
        <span>Risk Zones</span>
      </button>
    </div>
  )
}
