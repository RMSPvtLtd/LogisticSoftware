import type { Customer, Inquiry, Shipment, ShipmentStage, TransportMode } from "./api/types"

export interface ShipmentQuery {
  search: string
  atRisk: boolean
  onHold: boolean
  mode?: TransportMode
  origin?: string
  destination?: string
  stages: ShipmentStage[]
}

const text = (value: string | null | undefined) => value?.trim().toLocaleLowerCase() ?? ""

export function parseShipmentQuery(params: URLSearchParams): ShipmentQuery {
  const stages = (params.get("stage") ?? "")
    .split(",")
    .map((stage) => stage.trim())
    .filter(Boolean) as ShipmentStage[]
  const mode = params.get("mode")?.trim().toLowerCase() as TransportMode | undefined
  return {
    search: params.get("search")?.trim() ?? "",
    atRisk: params.get("at_risk") === "true",
    onHold: params.get("on_hold") === "true",
    mode: mode || undefined,
    origin: params.get("origin")?.trim() || undefined,
    destination: params.get("destination")?.trim() || undefined,
    stages,
  }
}

export function filterShipments(
  shipments: Shipment[],
  customers: Customer[],
  inquiries: Inquiry[],
  query: ShipmentQuery,
): Shipment[] {
  const customerById = new Map(customers.map((customer) => [customer.id, customer]))
  const inquiryById = new Map(inquiries.map((inquiry) => [inquiry.id, inquiry]))
  const search = text(query.search)
  const stages = new Set(query.stages)

  return shipments.filter((shipment) => {
    const customer = customerById.get(shipment.customer_id)
    const inquiry = inquiryById.get(shipment.inquiry_id)
    if (query.atRisk && !shipment.is_at_risk) return false
    if (query.onHold && !shipment.is_on_hold) return false
    if (query.mode && inquiry?.mode !== query.mode) return false
    if (query.origin && text(inquiry?.origin) !== text(query.origin)) return false
    if (query.destination && text(inquiry?.destination) !== text(query.destination)) return false
    if (stages.size && !stages.has(shipment.stage)) return false
    if (!search) return true
    const searchFields = [shipment.job_number, customer?.name, inquiry?.origin, inquiry?.destination, ...shipment.references.map((reference) => reference.value)]
    return searchFields.some((field) => text(field).includes(search))
  })
}
