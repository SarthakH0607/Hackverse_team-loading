import React from "react"
import { Navigation, Compass as CompassIcon } from "lucide-react"

interface CompassArrowProps {
  bearingDegrees: number // 0 - 360
  bearingLabel?: string // e.g. "038° NE"
  heading?: number // device heading if available, defaults to 0
  altitudeContour?: string // e.g. "+184m HIGH GROUND"
  distanceKm?: number // e.g. 1.4
  walkMinutes?: number // e.g. 20
}

export const CompassArrow: React.FC<CompassArrowProps> = ({
  bearingDegrees = 38,
  bearingLabel = "038° NE",
  heading = 0,
  altitudeContour = "+184m HIGH GROUND",
  distanceKm = 1.4,
  walkMinutes = 20,
}) => {
  // Arrow rotation relative to device heading
  const relativeAngle = (bearingDegrees - heading + 360) % 360

  return (
    <div className="w-full flex flex-col items-center select-none font-mono">
      {/* Top Telemetry Header */}
      <div className="w-full flex items-center justify-between text-xs mb-3 px-2">
        <div>
          <span className="text-[10px] text-neutral-400 block tracking-wider uppercase">
            BEARING AZIMUTH
          </span>
          <span className="text-neutral-100 font-bold text-sm">
            {bearingLabel}
          </span>
        </div>

        <div className="text-right">
          <span className="text-[10px] text-neutral-400 block tracking-wider uppercase">
            ALTITUDE CONTOUR
          </span>
          <span className="text-emerald-400 font-bold text-sm">
            {altitudeContour}
          </span>
        </div>
      </div>

      {/* Compass Dial Outer Ring */}
      <div className="relative w-56 h-56 rounded-full border-2 border-neutral-800 bg-neutral-950/80 shadow-2xl flex items-center justify-center my-2 p-3">
        {/* Cardinal tick marks */}
        <div className="absolute top-2 text-[11px] font-bold text-red-500">N</div>
        <div className="absolute right-2 text-[11px] font-bold text-neutral-400">E</div>
        <div className="absolute bottom-2 text-[11px] font-bold text-neutral-400">S</div>
        <div className="absolute left-2 text-[11px] font-bold text-neutral-400">W</div>

        {/* Diagonal tick marks */}
        <div className="absolute top-6 right-6 text-[9px] text-neutral-600">NE</div>
        <div className="absolute bottom-6 right-6 text-[9px] text-neutral-600">SE</div>
        <div className="absolute bottom-6 left-6 text-[9px] text-neutral-600">SW</div>
        <div className="absolute top-6 left-6 text-[9px] text-neutral-600">NW</div>

        {/* Circular reticle grooves */}
        <div className="absolute inset-5 rounded-full border border-neutral-800/60 pointer-events-none" />
        <div className="absolute inset-10 rounded-full border border-neutral-850/40 pointer-events-none" />
        <div className="absolute inset-16 rounded-full border border-dashed border-neutral-800 pointer-events-none" />

        {/* Rotating Compass Needle Container */}
        <div
          className="relative w-full h-full flex items-center justify-center transition-transform duration-500 ease-out"
          style={{ transform: `rotate(${relativeAngle}deg)` }}
        >
          {/* Target Guidance Needle */}
          <div className="absolute -top-1 flex flex-col items-center">
            {/* Arrow Head */}
            <div className="w-0 h-0 border-l-[10px] border-l-transparent border-r-[10px] border-r-transparent border-b-[24px] border-b-neutral-100 filter drop-shadow-[0_0_8px_rgba(255,255,255,0.4)]" />
            <div className="w-1.5 h-16 bg-neutral-100 rounded-sm" />
          </div>

          {/* South Tail */}
          <div className="absolute -bottom-1 flex flex-col items-center">
            <div className="w-1.5 h-16 bg-neutral-700 rounded-sm" />
            <div className="w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-t-[18px] border-t-neutral-700" />
          </div>

          {/* Center Hub */}
          <div className="relative z-10 w-8 h-8 rounded-full bg-neutral-900 border-2 border-neutral-200 flex items-center justify-center shadow-lg">
            <div className="w-2.5 h-2.5 rounded-full bg-white animate-pulse" />
          </div>
        </div>
      </div>

      {/* Advance Instruction Banner */}
      <div className="my-2 py-1 px-4 rounded bg-neutral-900/90 border border-neutral-800 text-center">
        <span className="text-[10px] tracking-wider font-bold text-neutral-200 uppercase flex items-center justify-center space-x-1.5">
          <span className="text-emerald-400">▲</span>
          <span>FACE ARROW &amp; ADVANCE FORWARD</span>
        </span>
      </div>

      {/* Radial Distance & Pace Cards */}
      <div className="w-full grid grid-cols-2 gap-3 mt-2">
        <div className="bg-neutral-900/80 border border-neutral-800 p-2.5 rounded text-left">
          <span className="text-[10px] text-neutral-400 uppercase tracking-wider block">
            RADIAL DISTANCE
          </span>
          <div className="flex items-baseline space-x-1 mt-0.5">
            <span className="text-2xl font-bold text-neutral-100 font-mono">
              {distanceKm}
            </span>
            <span className="text-xs text-neutral-400">km</span>
          </div>
        </div>

        <div className="bg-neutral-900/80 border border-neutral-800 p-2.5 rounded text-left">
          <span className="text-[10px] text-neutral-400 uppercase tracking-wider block">
            ESTIMATED PACE
          </span>
          <div className="flex items-baseline space-x-1 mt-0.5">
            <span className="text-2xl font-bold text-neutral-100 font-mono">
              {walkMinutes}
            </span>
            <span className="text-xs text-neutral-400">MIN WALK</span>
          </div>
        </div>
      </div>
    </div>
  )
}
