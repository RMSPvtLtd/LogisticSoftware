// Mirrors backend/schemas/tracking.py -- the backend is the single owner
// of this shape; nothing here is a second definition to keep in sync by
// hand, it's a read-only reflection of the API response for the compiler.

export interface TrackingEvent {
  type: string
  timestamp: string | null
}

// One voyage/cycle a container has been through. A container can have
// several (e.g. an earlier import leg and a later export leg), so
// TrackingResult carries a list of these, most-recent-first.
export interface ContainerDetail {
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

export interface TrackingResult {
  provider: string
  terminal: string
  container_number: string
  status: string
  status_code: string | null
  events: TrackingEvent[]
  details: ContainerDetail[]
}
