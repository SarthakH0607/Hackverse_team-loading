import React from "react"
import { ShieldCheck, Info } from "lucide-react"

interface ConfidenceLegendProps {
  score?: number // e.g. 96.8
  radarPassTime?: string
  opticalMatch?: boolean
}

export const ConfidenceLegend: React.FC<ConfidenceLegendProps> = ({
  score = 96.8,
  radarPassTime = "03-OCT 22:48 UTC",
  opticalMatch = true,
}) => {
  return (
    <div className="bg-neutral-950/90 border border-neutral-800/90 rounded-sm p-3 font-mono text-xs shadow-xl backdrop-blur-md max-w-md w-full">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-bold flex items-center space-x-1">
          <ShieldCheck className="w-3.5 h-3.5 text-neutral-300" />
          <span>DETECTION CONFIDENCE</span>
        </span>
        <span className="text-neutral-100 font-bold text-xs">{score.toFixed(1)}%</span>
      </div>

      {/* Gradient bar from Noise to Ground Truth */}
      <div className="relative mb-1">
        <div className="h-2 w-full rounded-full bg-gradient-to-r from-neutral-700 via-amber-600 to-red-500 border border-neutral-700/60" />
        {/* Needle marker at confidence score */}
        <div
          className="absolute top-0 -mt-1 w-2.5 h-4 bg-white border border-neutral-900 rounded-sm shadow-md -translate-x-1/2"
          style={{ left: `${Math.min(Math.max(score, 5), 98)}%` }}
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between text-[10px] text-neutral-400 mb-2">
        <span>Low confidence (Noise)</span>
        <span className="text-right">High confidence (Ground truth)</span>
      </div>

      {/* Technical annotation */}
      <div className="pt-2 border-t border-neutral-900 text-[10px] text-neutral-400 space-y-0.5 leading-snug">
        <div className="flex items-start space-x-1.5">
          <Info className="w-3 h-3 text-neutral-400 shrink-0 mt-0.5" />
          <div>
            <span className="text-neutral-300 font-medium">Analysis: </span>
            <span>Radar (penetrates heavy cloud cover).</span>
            {opticalMatch && (
              <span className="text-neutral-300 ml-1">
                Visual proof: Optical Sentinel-2 imagery match verified.
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
