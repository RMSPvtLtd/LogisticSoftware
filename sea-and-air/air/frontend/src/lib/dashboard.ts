// Pure aggregation functions for the Dashboard -- kept out of the view so
// the math is independently checkable. Every input here comes from data
// the app already fetches via existing endpoints (shipmentsApi.list(),
// quotesApi.list()); nothing here makes a network call or invents a field
// that isn't real.

import type { Quote, Shipment, ShipmentStage } from "@/lib/api/types"

export function activeShipmentsCount(shipments: Shipment[], indexOf: (s: ShipmentStage) => number, lastIndex: number): number {
  return shipments.filter((s) => indexOf(s.stage) < lastIndex).length
}

export function customsPendingCount(shipments: Shipment[]): number {
  return shipments.filter((s) => s.stage === "customs_examination" || s.stage === "customs_clearance").length
}

export function customsClearedCount(shipments: Shipment[], indexOf: (s: ShipmentStage) => number): number {
  const clearedIdx = indexOf("customs_clearance")
  if (clearedIdx < 0) return 0
  return shipments.filter((s) => indexOf(s.stage) > clearedIdx).length
}

export function airlineGroupCount(shipments: Shipment[], groupFor: (s: ShipmentStage) => string | null): number {
  return shipments.filter((s) => groupFor(s.stage) === "Airline").length
}

export function atRiskShipments(shipments: Shipment[]): Shipment[] {
  return shipments.filter((s) => s.is_at_risk)
}

export function expiringSoonQuotes(quotes: Quote[], withinDays = 3): Quote[] {
  const now = Date.now()
  const horizon = now + withinDays * 86_400_000
  return quotes.filter((q) => {
    if (q.status !== "sent") return false
    const t = new Date(q.valid_until).getTime()
    return t > now && t <= horizon
  })
}

export interface StageGroupCount {
  group: string
  count: number
}

// Stable order = first-seen order in the canonical stage list (useStages()),
// not alphabetical or insertion-order-of-shipments.
export function stageGroupBreakdown(
  shipments: Shipment[],
  groupFor: (s: ShipmentStage) => string | null,
  orderedGroups: string[],
): StageGroupCount[] {
  const counts = new Map<string, number>()
  for (const s of shipments) {
    const group = groupFor(s.stage) ?? "Other"
    counts.set(group, (counts.get(group) ?? 0) + 1)
  }
  const groups = orderedGroups.filter((g) => counts.has(g))
  if (counts.has("Other")) groups.push("Other")
  return groups.map((group) => ({ group, count: counts.get(group)! }))
}

export interface ActivityItem {
  shipment: Shipment
  text: string
}

// Derived from the shipment list's own stage+updated_at -- deliberately no
// per-shipment detail fetches (no global event-feed endpoint exists).
export function recentActivity(shipments: Shipment[], labelFor: (s: ShipmentStage) => string, limit = 8): ActivityItem[] {
  return [...shipments]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, limit)
    .map((s) => ({
      shipment: s,
      text: `${s.job_number ?? `Shipment #${s.id}`} is now at ${labelFor(s.stage)}`,
    }))
}
