import React, { useState } from "react"
import { MONITORED_SITES, SiteInfo } from "@/lib/data"
import { ChevronDown, MapPin, AlertCircle, Check, Clock } from "lucide-react"

interface SiteSwitcherProps {
  currentSite: SiteInfo
  onSelectSite: (site: SiteInfo) => void
}

export const SiteSwitcher: React.FC<SiteSwitcherProps> = ({
  currentSite,
  onSelectSite,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [showToast, setShowToast] = useState(false)

  const handleSelect = (site: SiteInfo) => {
    if (site.status === "coming_soon") {
      setShowToast(true)
      setTimeout(() => setShowToast(false), 3500)
      return
    }
    onSelectSite(site)
    setIsOpen(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 bg-neutral-900/90 hover:bg-neutral-800/90 border border-neutral-800 hover:border-neutral-700 px-3 py-1.5 rounded text-xs font-mono text-neutral-200 transition-colors shadow-sm focus:outline-none focus:ring-1 focus:ring-neutral-500"
        title="Select Target Area"
      >
        <MapPin className="w-3.5 h-3.5 text-neutral-400" />
        <span className="font-semibold truncate max-w-[220px] sm:max-w-[320px]">
          {currentSite.label}
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-neutral-400 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute left-0 mt-1.5 w-80 bg-neutral-950 border border-neutral-800 rounded-md shadow-2xl z-50 overflow-hidden divide-y divide-neutral-900 backdrop-blur-md">
            <div className="px-3 py-2 bg-neutral-900/60 text-[10px] font-mono uppercase tracking-wider text-neutral-400 flex items-center justify-between">
              <span>Select Operational Sector</span>
              <span className="text-neutral-500">2 Monitored</span>
            </div>

            {MONITORED_SITES.map((site) => {
              const isCurrent = site.id === currentSite.id
              const isComingSoon = site.status === "coming_soon"

              return (
                <div
                  key={site.id}
                  onClick={() => handleSelect(site)}
                  className={`p-3 transition-colors cursor-pointer flex items-start justify-between ${
                    isCurrent
                      ? "bg-neutral-900/80"
                      : isComingSoon
                      ? "hover:bg-neutral-900/40 opacity-80"
                      : "hover:bg-neutral-900/60"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-semibold text-neutral-100 font-mono">
                        {site.name}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-neutral-400 flex items-center space-x-2">
                      <span>{site.coordinates}</span>
                    </div>
                  </div>

                  <div>
                    {isComingSoon ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono bg-neutral-800 text-neutral-400 border border-neutral-700">
                        <Clock className="w-2.5 h-2.5 mr-1 text-amber-500" />
                        Coming soon
                      </span>
                    ) : (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
                        <Check className="w-2.5 h-2.5 mr-1" />
                        Active
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* Floating notice when clicked coming soon */}
      {showToast && (
        <div className="absolute top-full left-0 mt-2 z-50 w-72 bg-neutral-900 border border-amber-600/50 p-2.5 rounded shadow-lg animate-in fade-in slide-in-from-top-1 text-xs font-mono text-neutral-200">
          <div className="flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-400">Sector Data Pending</p>
              <p className="text-[11px] text-neutral-400 mt-0.5">
                SAR telemetry & high-resolution DEMs for Kedarnath are currently in calibration pipeline.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
