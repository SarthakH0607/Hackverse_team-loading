import React from "react"
import { Calendar, RotateCcw, ArrowLeftRight, Eye } from "lucide-react"

interface SwipeSliderProps {
  value: number // 0 to 100
  onChange: (value: number) => void
  onReset?: () => void
}

export const SwipeSlider: React.FC<SwipeSliderProps> = ({
  value,
  onChange,
  onReset,
}) => {
  return (
    <div className="bg-neutral-950/95 border border-neutral-750/90 rounded-md p-3.5 sm:p-4 font-mono shadow-2xl backdrop-blur-xl w-full max-w-xl select-none text-neutral-200">
      {/* Top Header with Prominent Stats & Mode Toggles */}
      <div className="flex items-center justify-between gap-2 mb-2.5">
        <div className="flex items-center space-x-2.5">
          <div className="w-6 h-6 rounded bg-neutral-900 border border-neutral-700 flex items-center justify-center text-red-400">
            <ArrowLeftRight className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-neutral-100 flex items-center space-x-2">
              <span>TEMPORAL SWIPE COMPARATOR</span>
              <span className="px-1.5 py-0.2 rounded bg-neutral-900 text-[10px] text-emerald-400 border border-emerald-900/60 font-semibold">
                ACTIVE
              </span>
            </div>
            <div className="text-[10px] text-neutral-400">
              Drag slider to inspect terrain &amp; flood damage
            </div>
          </div>
        </div>

        {/* Current Split Ratio Badge & Reset */}
        <div className="flex items-center space-x-2">
          <span className="px-2 py-0.5 rounded bg-neutral-900 border border-neutral-750 text-xs font-bold text-neutral-200">
            {Math.round(value)}% SPLIT
          </span>
          {onReset && (
            <button
              onClick={onReset}
              className="flex items-center space-x-1 text-xs text-neutral-300 hover:text-white bg-neutral-900 hover:bg-neutral-800 border border-neutral-750 px-2.5 py-1 rounded transition-colors active:scale-95"
              title="Reset handle to center (50%)"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Center</span>
            </button>
          )}
        </div>
      </div>

      {/* Enlarged Slider Bar with High-Visibility Track */}
      <div className="relative my-3 flex items-center">
        <input
          type="range"
          min="0"
          max="100"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full h-3 bg-neutral-800 hover:bg-neutral-750 rounded-lg appearance-none cursor-ew-resize accent-red-500 hover:accent-red-400 focus:outline-none transition-all shadow-inner"
        />
      </div>

      {/* Preset Quick-Jump Buttons */}
      <div className="grid grid-cols-3 gap-2 pt-1 pb-1">
        <button
          onClick={() => onChange(0)}
          className={`py-1 px-2 rounded text-[11px] font-semibold border transition-all text-center ${
            value === 0
              ? "bg-neutral-200 text-neutral-950 border-white shadow-md"
              : "bg-neutral-900/80 hover:bg-neutral-850 text-neutral-300 border-neutral-800 hover:border-neutral-700"
          }`}
        >
          100% Before
        </button>
        <button
          onClick={() => onChange(50)}
          className={`py-1 px-2 rounded text-[11px] font-semibold border transition-all text-center ${
            value === 50
              ? "bg-red-600 text-white border-red-400 shadow-md"
              : "bg-neutral-900/80 hover:bg-neutral-850 text-neutral-300 border-neutral-800 hover:border-neutral-700"
          }`}
        >
          50 / 50 Split
        </button>
        <button
          onClick={() => onChange(100)}
          className={`py-1 px-2 rounded text-[11px] font-semibold border transition-all text-center ${
            value === 100
              ? "bg-neutral-200 text-neutral-950 border-white shadow-md"
              : "bg-neutral-900/80 hover:bg-neutral-850 text-neutral-300 border-neutral-800 hover:border-neutral-700"
          }`}
        >
          100% After
        </button>
      </div>

      {/* Explanatory Corner Epoch Labels */}
      <div className="flex items-center justify-between text-[11px] text-neutral-400 pt-2 border-t border-neutral-900 mt-2">
        <div className="text-left">
          <span className="text-neutral-100 font-bold">LEFT:</span> Before (Sep 2023)
        </div>
        <div className="text-right">
          <span className="text-red-400 font-bold">RIGHT:</span> After (Oct 2023)
        </div>
      </div>
    </div>
  )
}
