import React from "react"
import { SafeZoneType } from "@/lib/data"
import { Cross, Shield, Droplets, Layers } from "lucide-react"

interface SafeZoneChipsProps {
  selectedType: SafeZoneType | "all"
  onSelectType: (type: SafeZoneType | "all") => void
  counts?: {
    all: number
    hospital: number
    shelter: number
    water: number
  }
}

export const SafeZoneChips: React.FC<SafeZoneChipsProps> = ({
  selectedType,
  onSelectType,
  counts,
}) => {
  const categories: {
    id: SafeZoneType | "all"
    label: string
    icon: React.ReactNode
  }[] = [
    {
      id: "all",
      label: "ALL",
      icon: <Layers className="w-3.5 h-3.5" />,
    },
    {
      id: "medical" as any, // maps to hospital for display
      label: "MEDICAL",
      icon: <Cross className="w-3.5 h-3.5" />,
    },
    {
      id: "shelter",
      label: "SHELTER",
      icon: <Shield className="w-3.5 h-3.5" />,
    },
    {
      id: "water",
      label: "WATER / RATIONS",
      icon: <Droplets className="w-3.5 h-3.5" />,
    },
  ]

  // Handle medical <-> hospital equivalence
  const isSelected = (id: string) => {
    if (id === "medical") return selectedType === "hospital"
    return selectedType === id
  }

  const handleSelect = (id: string) => {
    if (id === "medical") onSelectType("hospital")
    else onSelectType(id as SafeZoneType | "all")
  }

  return (
    <div className="w-full font-mono">
      <div className="text-[10px] uppercase tracking-wider text-neutral-400 font-bold mb-2 flex items-center justify-between">
        <span>ZONE PRIORITY CATEGORY</span>
      </div>

      <div className="grid grid-cols-3 sm:grid-cols-4 gap-1.5">
        {categories.map((cat) => {
          const active = isSelected(cat.id)

          return (
            <button
              key={cat.id}
              onClick={() => handleSelect(cat.id)}
              className={`flex flex-col items-center justify-center p-2 rounded-sm border transition-all text-xs ${
                active
                  ? "bg-neutral-100 text-neutral-950 font-bold border-white shadow-md"
                  : "bg-neutral-900/80 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-850 border-neutral-800"
              }`}
            >
              <div className="mb-1">{cat.icon}</div>
              <span className="text-[10px] tracking-tight">{cat.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
