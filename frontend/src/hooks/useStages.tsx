// Fetches the canonical ordered stage list + labels from GET /meta/stages
// once, and provides it via context. No component ever hardcodes a stage
// label or stage order -- that mapping lives only on the backend
// (app/models/enums.py) and is read from here.

import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { metaApi } from "@/lib/api/client"
import type { ShipmentStage, StageMeta } from "@/lib/api/types"

interface StagesContextValue {
  stages: StageMeta[]
  loading: boolean
  labelFor: (stage: ShipmentStage) => string
  indexOf: (stage: ShipmentStage) => number
}

const StagesContext = createContext<StagesContextValue | null>(null)

export function StagesProvider({ children }: { children: ReactNode }) {
  const [stages, setStages] = useState<StageMeta[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    metaApi
      .stages()
      .then((res) => {
        if (!cancelled) setStages(res.stages)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const value: StagesContextValue = {
    stages,
    loading,
    labelFor: (stage) => stages.find((s) => s.stage === stage)?.label ?? stage,
    indexOf: (stage) => stages.findIndex((s) => s.stage === stage),
  }

  return <StagesContext.Provider value={value}>{children}</StagesContext.Provider>
}

export function useStages() {
  const ctx = useContext(StagesContext)
  if (!ctx) throw new Error("useStages must be used within a StagesProvider")
  return ctx
}
