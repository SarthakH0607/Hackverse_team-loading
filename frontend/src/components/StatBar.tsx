import React from "react"
import { AlertTriangle, Radio, Users } from "lucide-react"

interface StatBarProps {
  affectedAreaKm2: number
  peopleAtRisk: number
  criticalNodes: number
}

export const StatBar: React.FC<StatBarProps> = ({
  affectedAreaKm2 = 86.3,
  peopleAtRisk = 24858,
  criticalNodes = 14,
}) => {
  return (
    <div className="w-full bg-neutral-950/90 border-b border-neutral-800/80 px-4 py-2 text-xs font-mono backdrop-blur-sm">
      <div className="flex flex-wrap items-center justify-between gap-y-2 gap-x-6">
        {/* Left Metrics Group */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          {/* Affected Area */}
          <div className="flex items-center space-x-2">
            <span className="text-neutral-400 uppercase tracking-wider text-[11px]">
              AFFECTED AREA:
            </span>
            <div className="flex items-baseline space-x-1.5">
              <span className="text-neutral-100 font-bold text-sm">
                {affectedAreaKm2.toLocaleString()}
              </span>
              <span className="text-neutral-400 text-xs">km²</span>
              <span className="text-neutral-400 text-[10px]">(estimate)</span>
            </div>
          </div>

          <div className="hidden sm:block h-3.5 w-px bg-neutral-800" />

          {/* People At Risk */}
          <div className="flex items-center space-x-2">
            <Users className="w-3.5 h-3.5 text-neutral-400" />
            <span className="text-neutral-400 uppercase tracking-wider text-[11px]">
              PEOPLE AT RISK:
            </span>
            <span className="text-neutral-100 font-bold text-sm">
              {peopleAtRisk.toLocaleString()}
            </span>
            <span className="text-neutral-400 text-[11px]">civilians (estimate)</span>
          </div>

          <div className="hidden sm:block h-3.5 w-px bg-neutral-800" />

          {/* Villages Flagged */}
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
            <span className="text-neutral-400 uppercase tracking-wider text-[11px]">
              VILLAGES FLAGGED:
            </span>
            <span className="text-red-400 font-bold text-sm">
              {criticalNodes}
            </span>
            <span className="text-neutral-400 text-[11px]">priority nodes</span>
          </div>
        </div>

        {/* Right Status Group */}
        <div className="flex items-center space-x-2 text-[11px] text-neutral-400 ml-auto sm:ml-0">
          <Radio className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-neutral-300 font-mono tracking-tight text-[11px]">
            SATELLITE INTEL // MONITORING ACTIVE
          </span>
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
        </div>
      </div>
    </div>
  )
}
