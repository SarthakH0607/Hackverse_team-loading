import React from "react"
import { VillageFeature } from "@/lib/data"
import { Users, AlertTriangle, ShieldCheck, ChevronRight, Activity, Radio, Hospital, Route } from "lucide-react"

interface RankedCardProps {
  feature: VillageFeature
  isSelected?: boolean
  onSelect?: (feature: VillageFeature) => void
}

export const RankedCard: React.FC<RankedCardProps> = ({
  feature,
  isSelected = false,
  onSelect,
}) => {
  const p = feature.properties

  // Priority based on ranking and relative severity
  const priority = p.priority || (
    p.rank <= 3 ? "CRITICAL" :
    p.rank <= 10 ? "HIGH" :
    p.rank <= 25 ? "ELEVATED" :
    p.rank <= 45 ? "MONITORED" : "STABLE"
  )

  const getPriorityBadge = () => {
    switch (priority) {
      case "CRITICAL":
        return {
          bg: "bg-red-600 text-white font-bold",
          border: "border-red-600",
          cardBorder: "border-red-600/60 bg-red-950/10",
          indicator: "bg-red-500",
        }
      case "HIGH":
        return {
          bg: "bg-orange-500 text-white font-semibold",
          border: "border-orange-500",
          cardBorder: "border-orange-500/40 bg-orange-950/10",
          indicator: "bg-orange-400",
        }
      case "ELEVATED":
        return {
          bg: "bg-amber-500/20 text-amber-300 border border-amber-500/50 font-semibold",
          border: "border-amber-500/50",
          cardBorder: "border-amber-500/30 bg-amber-950/10",
          indicator: "bg-amber-400",
        }
      case "MONITORED":
        return {
          bg: "bg-neutral-800 text-neutral-300 border border-neutral-700 font-semibold",
          border: "border-neutral-700",
          cardBorder: "border-neutral-800 bg-neutral-900/30",
          indicator: "bg-neutral-400",
        }
      case "STABLE":
      default:
        return {
          bg: "bg-emerald-950 text-emerald-400 border border-emerald-800/80 font-semibold",
          border: "border-emerald-800/80",
          cardBorder: "border-emerald-900/30 bg-emerald-950/10",
          indicator: "bg-emerald-500",
        }
    }
  }

  const badgeStyle = getPriorityBadge()

  // Extract metrics from reason string
  const hospitalRaw = p.reason?.match(/nearest unaffected hospital\s*([\d.]+\s*km away)/i) || p.reason?.match(/([\d.]+\s*km to nearest hospital)/i)
  const hospitalText = hospitalRaw ? (hospitalRaw[1] || hospitalRaw[0]) : null

  const impactRaw = p.reason?.match(/([\d.]+%\s*of area changed)/i) || p.reason?.match(/([\d.]+%\s*area affected)/i)
  const impactText = impactRaw ? (impactRaw[1] || impactRaw[0]) : null

  const roadRaw = p.reason?.match(/(access roads mostly blocked|some access road blocked|roads accessible)/i)
  const roadText = p.roadStatus || (roadRaw ? roadRaw[1] : null)

  const formatScoreDisplay = () => {
    if (p.confidence) return p.confidence
    if (p.score > 100) return `Score ${Math.round(p.score).toLocaleString()}`
    if (p.score > 1) return `Score ${p.score.toFixed(1)}`
    return `${Math.round(p.score * 100)}% index`
  }

  return (
    <div
      onClick={() => onSelect?.(feature)}
      className={`relative group cursor-pointer transition-all duration-200 border rounded-sm p-3 font-mono text-left ${
        isSelected
          ? `bg-neutral-900/90 border-neutral-400 ring-1 ring-neutral-400 shadow-lg`
          : `bg-neutral-950/70 hover:bg-neutral-900/60 border-neutral-800/80 hover:border-neutral-700`
      }`}
    >
      {/* Accent left indicator stripe */}
      <div
        className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-sm ${
          isSelected ? badgeStyle.indicator : "bg-transparent group-hover:bg-neutral-700"
        }`}
      />

      {/* Top Header: Rank, Name, Priority Badge */}
      <div className="flex items-start justify-between gap-2 mb-1.5 pl-1">
        <div className="flex items-baseline space-x-1.5 min-w-0">
          <span className="text-neutral-400 text-xs font-semibold">
            #{p.rank.toString().padStart(2, "0")}
          </span>
          <h3 className="text-neutral-100 font-bold text-xs sm:text-sm truncate">
            {p.name}
          </h3>
        </div>

        <span
          className={`shrink-0 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-sm ${badgeStyle.bg}`}
        >
          {priority} {priority === "CRITICAL" ? "PRIORITY" : "RISK"}
        </span>
      </div>

      {/* Population & Region */}
      <div className="flex items-center space-x-2 text-[11px] text-neutral-400 mb-2 pl-1">
        <Users className="w-3 h-3 text-neutral-400 shrink-0" />
        <span className="text-neutral-300 font-medium">
          {p.population.toLocaleString()} civilians
        </span>
        {p.region ? (
          <>
            <span className="text-neutral-600">•</span>
            <span className="text-neutral-400 truncate">{p.region}</span>
          </>
        ) : (
          <>
            <span className="text-neutral-600">•</span>
            <span className="text-neutral-400 text-[10px]">{formatScoreDisplay()}</span>
          </>
        )}
      </div>

      {/* Reason / Impact */}
      <p className="text-[11px] text-neutral-300 line-clamp-2 leading-relaxed mb-2.5 pl-1">
        {p.reason}
      </p>

      {/* Key Surge / Infrastructure Metrics */}
      {(p.waterSurgeDelta || impactText || hospitalText || roadText || p.isolatedCount) && (
        <div className="grid grid-cols-2 gap-1.5 bg-neutral-900/80 p-2 rounded border border-neutral-800/80 text-[10px] mb-2.5 ml-1">
          {p.waterSurgeDelta ? (
            <div>
              <span className="text-neutral-400 block text-[9px]">WATER SURGE:</span>
              <span className="text-red-400 font-bold">{p.waterSurgeDelta}</span>
            </div>
          ) : impactText ? (
            <div>
              <span className="text-neutral-400 block text-[9px]">FLOOD IMPACT:</span>
              <span className="text-amber-400 font-bold">{impactText}</span>
            </div>
          ) : null}

          {p.isolatedCount ? (
            <div>
              <span className="text-neutral-400 block text-[9px]">CASUALTY EST:</span>
              <span className="text-amber-400 font-medium">{p.isolatedCount}</span>
            </div>
          ) : hospitalText ? (
            <div>
              <span className="text-neutral-400 block text-[9px]">HOSPITAL DIST:</span>
              <span className="text-neutral-200 font-medium truncate block">{hospitalText}</span>
            </div>
          ) : null}

          {roadText && (
            <div className="col-span-2 pt-1 border-t border-neutral-800 text-[10px] flex items-center justify-between">
              <span className="text-neutral-400">ACCESS ROADS:</span>
              <span className="text-neutral-200 font-medium capitalize">{roadText}</span>
            </div>
          )}
        </div>
      )}

      {/* Footer: Confidence, Sensor status */}
      <div className="flex items-center justify-between text-[10px] text-neutral-400 pt-1 border-t border-neutral-900 pl-1">
        <div className="flex items-center space-x-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>{formatScoreDisplay()}</span>
        </div>

        <div className="flex items-center space-x-1 text-neutral-400 group-hover:text-neutral-200">
          <span className="uppercase text-[9px] font-bold tracking-wider">
            {isSelected ? "ACTIVE FOCUS" : "INSPECT"}
          </span>
          <ChevronRight className="w-3 h-3" />
        </div>
      </div>
    </div>
  )
}
