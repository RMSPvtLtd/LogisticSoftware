// Ops's ShipmentDetailPage gets a raw Shipment (stage + status_events), not
// the precomputed TrackingChecklistItem[] the backend's tracking/customer-
// portal endpoints return. This derives the same shape client-side from
// data already fetched -- no new endpoint.

import type { ChecklistStatus, ShipmentStage, StageMeta, StatusEvent, TrackingChecklistItem } from "@/lib/api/types"

export function buildChecklist(
  stages: StageMeta[],
  currentStage: ShipmentStage,
  events: StatusEvent[],
): TrackingChecklistItem[] {
  const currentIndex = stages.findIndex((s) => s.stage === currentStage)
  return stages.map((s, i) => {
    const status: ChecklistStatus = i < currentIndex ? "completed" : i === currentIndex ? "current" : "upcoming"
    const event = events.find((e) => e.stage === s.stage && e.is_stage_change)
    return { stage: s.stage, status, timestamp: event?.timestamp ?? null }
  })
}
