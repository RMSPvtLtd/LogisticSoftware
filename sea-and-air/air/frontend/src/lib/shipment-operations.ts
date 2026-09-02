export interface ShipmentOperationState {
  stage: string
  is_at_risk: boolean
  is_on_hold: boolean
  priority: string
}

export interface StageEntry {
  stage: string
  timestamp: string
  is_stage_change: boolean
}

export interface JourneyStage {
  stage: string
  label: string
  group: string | null
}

export interface JourneyRailItem {
  label: string
  state: "completed" | "current" | "upcoming"
}

export function quickViewCounts(shipments: ShipmentOperationState[]) {
  return {
    all: shipments.length,
    attention: shipments.filter((shipment) => shipment.is_at_risk || shipment.is_on_hold).length,
    atRisk: shipments.filter((shipment) => shipment.is_at_risk).length,
    onHold: shipments.filter((shipment) => shipment.is_on_hold).length,
    highPriority: shipments.filter((shipment) => shipment.priority === "high").length,
    readyToInvoice: shipments.filter((shipment) => shipment.stage === "arrival").length,
    completed: shipments.filter((shipment) => shipment.stage === "invoice_to_customer").length,
  }
}

export function stageEnteredAt(stage: string, events: StageEntry[]): string | null {
  return [...events].reverse().find((event) => event.stage === stage && event.is_stage_change)?.timestamp ?? null
}

export function formatWaitingAge(enteredAt: string | null, now = new Date()): string {
  if (!enteredAt) return "—"
  const minutes = Math.max(0, Math.floor((now.getTime() - new Date(enteredAt).getTime()) / 60_000))
  if (minutes < 1) return "Just now"
  const days = Math.floor(minutes / 1_440)
  const hours = Math.floor((minutes % 1_440) / 60)
  const remainder = minutes % 60
  if (days) return `${days}d ${hours}h`
  if (hours) return `${hours}h ${remainder}m`
  return `${remainder}m`
}

export function journeyRail(stages: JourneyStage[], currentStage: string): JourneyRailItem[] {
  const currentIndex = stages.findIndex((stage) => stage.stage === currentStage)
  const groups = stages.reduce<{ label: string; firstIndex: number; lastIndex: number }[]>((items, stage, index) => {
    const label = stage.group ?? stage.label
    const last = items.at(-1)
    if (last?.label === label) {
      last.lastIndex = index
    } else {
      items.push({ label, firstIndex: index, lastIndex: index })
    }
    return items
  }, [])

  return groups.map((group) => ({
    label: group.label,
    state: currentIndex > group.lastIndex ? "completed" : currentIndex >= group.firstIndex ? "current" : "upcoming",
  }))
}

export function attentionText(shipment: Pick<ShipmentOperationState, "is_at_risk" | "is_on_hold">): string | null {
  if (shipment.is_on_hold && shipment.is_at_risk) return "On hold · At risk"
  if (shipment.is_on_hold) return "On hold"
  if (shipment.is_at_risk) return "At risk"
  return null
}

export function withShipmentSearch(params: URLSearchParams, search: string): URLSearchParams {
  const next = new URLSearchParams(params)
  if (search) next.set("search", search)
  else next.delete("search")
  return next
}
