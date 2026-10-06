import React from "react"
import { Sliders, SplitSquareVertical, Calendar } from "lucide-react"

interface SwipeSliderProps {
  value: number // 0 to 100
  onChange: (value: number) => void
  isSplitEngaged?: boolean
  onToggleSplit?: () => void
  surgeDeltaText?: string
}

export const SwipeSlider: React.FC<SwipeSliderProps> = ({
  value,
  onChange,
  isSplitEngaged = true,
  onToggleSplit,
  surgeDeltaText = "+184% water extent",
}) => {
  return (
    <div className="bg-neutral-950/95 border border-neutral-800/90 rounded-sm p-3 font-mono text-xs shadow-xl backdrop-blur-md w-full max-w-xl">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <Calendar className="w-3.5 h-3.5 text-neutral-400" />
          <span className="text-[10px] uppercase tracking-wider text-neutral-300 font-bold">
            TEMPORAL COMPARISON
          </span>
          {isSplitEngaged && (
            <span className="px-1.5 py-0.5 rounded bg-neutral-800 text-[9px] text-amber-400 border border-neutral-700 font-semibold">
              {Math.round(value)}% DUAL-SPLIT
            </span>
          )}
        </div>

        {onToggleSplit && (
          <button
            onClick={onToggleSplit}
            className="flex items-center space-x-1 text-[10px] text-neutral-400 hover:text-neutral-200 transition-colors"
          >
            <SplitSquareVertical className="w-3 h-3" />
            <span>{isSplitEngaged ? "Reset Split" : "Engage Split"}</span>
          </button>
        )}
      </div>

      {/* Slider Bar */}
      <div className="relative my-3 flex items-center">
        <input
          type="range"
          min="0"
          max="100"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full h-1.5 bg-neutral-800 rounded-lg appearance-none cursor-pointer accent-neutral-200 hover:accent-white focus:outline-none focus:ring-1 focus:ring-neutral-500"
        />
      </div>

      {/* Labels & Delta */}
      <div className="flex items-center justify-between text-[11px] pt-1">
        <div className="text-left">
          <div className="text-neutral-100 font-semibold">Before (Sep 2023)</div>
          <div className="text-[9px] text-neutral-400">SAR Sentinel-1 Baseline</div>
        </div>

        <div className="text-center px-2 py-0.5 rounded bg-red-950/40 border border-red-900/60 text-red-400 font-bold text-[10px]">
          {surgeDeltaText}
        </div>

        <div className="text-right">
          <div className="text-neutral-100 font-semibold">After (Oct 2023 flood)</div>
          <div className="text-[9px] text-neutral-400">Post-event Optical + Radar</div>
        </div>
      </div>
    </div>
  )
}
