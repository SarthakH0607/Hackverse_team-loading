import React from "react"
import { Layers, Eye, EyeOff } from "lucide-react"

export interface LayerState {
  changeActive: boolean
  riskOverlay: boolean
  priorityNodes: boolean
  safeZones: boolean
}

interface LayerTogglesProps {
  layers: LayerState
  onToggle: (layer: keyof LayerState) => void
}

export const LayerToggles: React.FC<LayerTogglesProps> = ({
  layers,
  onToggle,
}) => {
  return (
    <div className="flex flex-wrap items-center gap-1.5 bg-neutral-950/90 border border-neutral-800/90 p-1 rounded-sm shadow-xl backdrop-blur-md font-mono text-[11px]">
      <div className="px-2 py-1 text-neutral-400 border-r border-neutral-800 hidden sm:flex items-center space-x-1.5">
        <Layers className="w-3 h-3 text-neutral-400" />
        <span className="uppercase text-[10px] tracking-wider font-semibold">LAYERS</span>
      </div>

      {/* Change Layer */}
      <button
        onClick={() => onToggle("changeActive")}
        className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-sm transition-all ${
          layers.changeActive
            ? "bg-neutral-800 text-neutral-100 font-semibold border border-neutral-600 shadow-sm"
            : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900 border border-transparent"
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            layers.changeActive ? "bg-red-500 animate-pulse" : "bg-neutral-600"
          }`}
        />
        <span>Change</span>
        {layers.changeActive && (
          <span className="text-[9px] text-neutral-400 font-normal">(Active)</span>
        )}
      </button>

      {/* Risk Overlay */}
      <button
        onClick={() => onToggle("riskOverlay")}
        className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-sm transition-all ${
          layers.riskOverlay
            ? "bg-neutral-800 text-neutral-100 font-semibold border border-neutral-600 shadow-sm"
            : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900 border border-transparent"
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            layers.riskOverlay ? "bg-amber-500" : "bg-neutral-600"
          }`}
        />
        <span>Risk Overlay</span>
        {layers.riskOverlay && (
          <span className="text-[9px] text-neutral-400 font-normal">(Active)</span>
        )}
      </button>

      {/* Priority Nodes */}
      <button
        onClick={() => onToggle("priorityNodes")}
        className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-sm transition-all ${
          layers.priorityNodes
            ? "bg-neutral-800 text-neutral-100 font-semibold border border-neutral-600 shadow-sm"
            : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900 border border-transparent"
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            layers.priorityNodes ? "bg-blue-400" : "bg-neutral-600"
          }`}
        />
        <span>Priority</span>
      </button>

      {/* Safe Zones */}
      <button
        onClick={() => onToggle("safeZones")}
        className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-sm transition-all ${
          layers.safeZones
            ? "bg-neutral-800 text-neutral-100 font-semibold border border-neutral-600 shadow-sm"
            : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900 border border-transparent"
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            layers.safeZones ? "bg-emerald-400" : "bg-neutral-600"
          }`}
        />
        <span>Safe Zones</span>
      </button>
    </div>
  )
}
