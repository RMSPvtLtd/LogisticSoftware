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

export type ReferenceType =
  | "JOB_NUMBER"
  | "MAWB"
  | "HAWB"
  | "MBL"
  | "HBL"
  | "CONTAINER"
  | "FORM_E"
  | "LC"
  | "PARTY_REFERENCE"

export type ChargeKind = "freight" | "documentation" | "customs" | "pickup" | "handling" | "other"

export type ChecklistStatus = "completed" | "current" | "upcoming"

export type Priority = "low" | "medium" | "high"

export type InvoiceStatus = "draft" | "issued" | "paid" | "cancelled"

// Decimal fields are serialized by the backend as JSON strings (Pydantic's
// default), not numbers -- keeping them as `string` here avoids silent
// float-precision loss; format with `formatMoney` / `Number()` at render time.

export interface Customer {
  id: number
  name: string
  company_name: string | null
  email: string
  phone: string | null
  address: string | null
  username: string | null
  portal_active: boolean
  created_at: string
  updated_at: string
}

export interface CustomerPortalCredentials {
  username: string
  password: string
}

export interface CustomerCreate {
  name: string
  company_name?: string | null
  email: string
  phone?: string | null
  address?: string | null
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
  hs_code: string | null
  pieces: number | null
  supplier_name: string | null
  supplier_address: string | null
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
  hs_code?: string | null
  pieces?: number | null
  supplier_name?: string | null
  supplier_address?: string | null
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
  shipment_stage: ShipmentStage | null
  invoice_id: number | null
  currency: string
  subtotal: string
  markup_amount: string
  tax_amount: string
  discount_amount: string
  total: string
  valid_until: string
  created_at: string
  updated_at: string
  line_items: QuoteLineItem[]
}

export interface QuoteAdjustments {
  tax_amount: string
  discount_amount: string
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
  priority: Priority
  carrier: string | null
  voyage_flight_number: string | null
  created_at: string
  updated_at: string
  references: ShipmentReference[]
  status_events: StatusEvent[]
}

export interface ShipmentFilters {
  stage?: ShipmentStage
  at_risk?: boolean
  mode?: TransportMode
  priority?: Priority
}

export interface ShipmentDocument {
  id: number
  shipment_id: number
  stage: ShipmentStage
  filename: string
  content_type: string
  size_bytes: number
  uploaded_by: string
  created_at: string
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

// --- sea vertical: container tracking (separate backend, see
// sea-and-air/sea/backend/schemas/tracking.py -- mirrors that shape
// exactly, "Sea"-prefixed here only to avoid colliding with air's own
// TrackingResult/TrackingEvent above, which are a different shape) ---

export interface SeaTrackingEvent {
  type: string
  timestamp: string | null
}

export interface SeaContainerDetail {
  owner: string | null
  bl_number: string | null
  container_size_type: string | null
  category: string | null
  status_code: string | null
  vessel_voyage: string | null
  vir_number: string | null
  eta: string | null
  etd: string | null
  discharge_time: string | null
  load_time: string | null
  do_issuance_date: string | null
  do_expiry_date: string | null
  gate_in_time: string | null
  gate_out_time: string | null
  origin: string | null
  destination: string | null
  custom_seal_number: string | null
  line_seal_number: string | null
  security_seal_number: string | null
  other_seal_number: string | null
  custom_status: string | null
  current_position: string | null
  commodity: string | null
  weight: string | null
  weighment: string | null
  scanning: string | null
  present_holds: string | null
}

export interface SeaTrackingResult {
  provider: string
  terminal: string
  container_number: string
  status: string
  status_code: string | null
  events: SeaTrackingEvent[]
  details: SeaContainerDetail[]
}

export interface StageMeta {
  stage: ShipmentStage
  label: string
  group: string | null
}

// --- companies (issuing entities) and invoices ---

export interface Company {
  id: number
  name: string
  address: string
  phone: string | null
  email: string | null
  website: string | null
  tax_id_label: string | null
  tax_id: string | null
  company_reg_no: string | null
  is_default: boolean
}

export interface InvoiceLineItem {
  id: number
  kind: ChargeKind
  description: string
  quantity: string
  unit_price: string
  amount: string
}

export interface Invoice {
  id: number
  invoice_number: string
  quote_id: number
  shipment_id: number
  customer_id: number
  company_id: number
  status: InvoiceStatus
  issued_date: string
  currency: string
  subtotal: string
  markup_amount: string
  tax_amount: string
  discount_amount: string
  total: string
  customer_name_snapshot: string
  customer_address_snapshot: string | null
  supplier_name_snapshot: string | null
  supplier_address_snapshot: string | null
  origin_snapshot: string
  destination_snapshot: string
  mode_snapshot: string
  incoterm_snapshot: string
  hs_code_snapshot: string | null
  pieces_snapshot: number | null
  weight_kg_snapshot: string
  volume_cbm_snapshot: string
  chargeable_weight_kg_snapshot: string
  carrier_snapshot: string | null
  voyage_flight_number_snapshot: string | null
  job_number_snapshot: string | null
  created_at: string
  line_items: InvoiceLineItem[]
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

// --- customer portal ---

export interface CustomerLoginResponse {
  access_token: string
  token_type: string
  customer: Customer
}

export interface CustomerShipmentSummary {
  id: number
  job_number: string | null
  origin: string
  destination: string
  stage: ShipmentStage
  is_at_risk: boolean
  updated_at: string
}
