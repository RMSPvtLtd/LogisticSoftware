// Mirrors backend/app/models/enums.py -- the backend is the single owner of
// these value sets; this file is a read-only reflection of them for the
// compiler, not a second definition to keep in sync by hand elsewhere in
// the UI (components read stage order/labels from the /meta/stages API,
// never redeclare it).

export type ShipmentStage =
  | "inquiry"
  | "quotation"
  | "job_opening"
  | "airway_bill"
  | "gd"
  | "pickup"
  | "gate_in"
  | "shipment_receipt"
  | "weighment"
  | "customs_examination"
  | "customs_clearance"
  | "scanning"
  | "handover"
  | "departure"
  | "transhipment"
  | "arrival"
  | "invoice_to_customer"

export type TransportMode = "air" | "sea" | "road"

export type QuoteStatus = "draft" | "sent" | "accepted" | "expired"

export type EventSource = "manual" | "automated" | "system" | "correction"

export type ReferenceType = "JOB_NUMBER" | "MAWB" | "HAWB" | "MBL" | "HBL" | "CONTAINER"

export type ChargeKind = "freight" | "documentation" | "customs" | "pickup" | "handling" | "other"

export type ChecklistStatus = "completed" | "current" | "upcoming"

// Decimal fields are serialized by the backend as JSON strings (Pydantic's
// default), not numbers -- keeping them as `string` here avoids silent
// float-precision loss; format with `formatMoney` / `Number()` at render time.

export interface Customer {
  id: number
  name: string
  company_name: string | null
  email: string
  phone: string | null
  created_at: string
  updated_at: string
}

export interface CustomerCreate {
  name: string
  company_name?: string | null
  email: string
  phone?: string | null
}

export interface Inquiry {
  id: number
  customer_id: number
  origin: string
  destination: string
  mode: TransportMode
  cargo_type: string
  weight_kg: string
  volume_cbm: string
  dimensions: string | null
  ready_date: string | null
  incoterm: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface InquiryCreate {
  customer_id: number
  origin: string
  destination: string
  mode: TransportMode
  cargo_type: string
  weight_kg: string
  volume_cbm: string
  dimensions?: string | null
  ready_date?: string | null
  incoterm: string
  description?: string | null
}

export interface QuoteLineItem {
  id: number
  kind: ChargeKind
  description: string
  quantity: string
  unit_price: string
  calculated_total: string
  final_total: string
  markup_amount: string
  is_manual_override: boolean
}

export interface Quote {
  id: number
  inquiry_id: number
  status: QuoteStatus
  currency: string
  subtotal: string
  markup_amount: string
  total: string
  valid_until: string
  created_at: string
  updated_at: string
  line_items: QuoteLineItem[]
}

export interface LineItemOverride {
  line_item_id: number
  final_total: string
}

export interface ShipmentReference {
  id: number
  type: ReferenceType
  value: string
  created_at: string
}

export interface StatusEvent {
  id: number
  stage: ShipmentStage
  timestamp: string
  actor: string
  note: string | null
  source: EventSource
  is_stage_change: boolean
  is_internal: boolean
}

export interface Shipment {
  id: number
  customer_id: number
  inquiry_id: number
  quote_id: number | null
  job_number: string | null
  stage: ShipmentStage
  is_at_risk: boolean
  risk_reason: string | null
  created_at: string
  updated_at: string
  references: ShipmentReference[]
  status_events: StatusEvent[]
}

export interface ShipmentFilters {
  stage?: ShipmentStage
  at_risk?: boolean
  mode?: TransportMode
}

export interface TrackingChecklistItem {
  stage: ShipmentStage
  status: ChecklistStatus
  timestamp: string | null
}

export interface TrackingReference {
  type: ReferenceType
  value: string
}

export interface TrackingEvent {
  stage: ShipmentStage
  timestamp: string
  note: string | null
}

export interface TrackingResult {
  job_number: string | null
  origin: string
  destination: string
  mode: TransportMode
  stage: ShipmentStage
  checklist: TrackingChecklistItem[]
  status_history: TrackingEvent[]
  references: TrackingReference[]
  at_risk: boolean
}

export interface StageMeta {
  stage: ShipmentStage
  label: string
  group: string | null
}

// --- worker portal / auth ---

export interface Area {
  id: number
  name: string
  stage: ShipmentStage
}

export interface Worker {
  id: number
  name: string
  username: string
  is_active: boolean
  area: Area
  created_at: string
}

export interface WorkerCreate {
  name: string
  username: string
  password: string
  area_id: number
}

export interface LoginResponse {
  access_token: string
  token_type: string
  worker: Worker
}

export interface WorkerQueueItem {
  id: number
  job_number: string
  customer_name: string
  origin: string
  destination: string
  cargo_type: string
  waiting_since: string
  last_note: string | null
}
