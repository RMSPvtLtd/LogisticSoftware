// Thin, typed wrapper around the Raaziq backend REST API. Every call goes
// through `request`, so error handling (the backend's centralized
// `{"detail": "..."}` shape) and the base URL are each defined once, not
// repeated at every call site.

import type {
  Customer,
  CustomerCreate,
  Inquiry,
  InquiryCreate,
  LineItemOverride,
  Quote,
  Shipment,
  ShipmentFilters,
  StageMeta,
  TrackingResult,
} from "./types"

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api"

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = "ApiError"
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (typeof body?.detail === "string") detail = body.detail
      else if (Array.isArray(body?.detail)) {
        // FastAPI/Pydantic validation errors: a list of {loc, msg, ...}.
        detail = body.detail.map((e: { msg?: string }) => e.msg).filter(Boolean).join("; ") || detail
      }
    } catch {
      // response body wasn't JSON -- fall back to statusText
    }
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

function qs(params: object): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined)
  if (entries.length === 0) return ""
  return "?" + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()
}

// --- customers ---

export const customersApi = {
  list: () => request<Customer[]>("/customers"),
  get: (id: number) => request<Customer>(`/customers/${id}`),
  create: (payload: CustomerCreate) =>
    request<Customer>("/customers", { method: "POST", body: JSON.stringify(payload) }),
}

// --- inquiries ---

export const inquiriesApi = {
  list: () => request<Inquiry[]>("/inquiries"),
  get: (id: number) => request<Inquiry>(`/inquiries/${id}`),
  create: (payload: InquiryCreate) =>
    request<Inquiry>("/inquiries", { method: "POST", body: JSON.stringify(payload) }),
}

// --- quotes ---

export const quotesApi = {
  list: () => request<Quote[]>("/quotes"),
  get: (id: number) => request<Quote>(`/quotes/${id}`),
  generate: (inquiryId: number) =>
    request<Quote>("/quotes/generate", { method: "POST", body: JSON.stringify({ inquiry_id: inquiryId }) }),
  overrideLineItems: (id: number, overrides: LineItemOverride[]) =>
    request<Quote>(`/quotes/${id}/line-items`, { method: "PATCH", body: JSON.stringify({ overrides }) }),
  send: (id: number) => request<Quote>(`/quotes/${id}/send`, { method: "POST" }),
  accept: (id: number) => request<Shipment>(`/quotes/${id}/accept`, { method: "POST" }),
}

// --- shipments ---

export const shipmentsApi = {
  list: (filters: ShipmentFilters = {}) => request<Shipment[]>(`/shipments${qs(filters)}`),
  get: (id: number) => request<Shipment>(`/shipments/${id}`),
  updateStatus: (id: number, stage: string, note?: string) =>
    request<Shipment>(`/shipments/${id}/status`, { method: "POST", body: JSON.stringify({ stage, note }) }),
  correctStatus: (id: number, stage: string, reason: string) =>
    request<Shipment>(`/shipments/${id}/status/correct`, {
      method: "POST",
      body: JSON.stringify({ stage, reason }),
    }),
  addReference: (id: number, type: string, value: string) =>
    request<Shipment>(`/shipments/${id}/references`, { method: "POST", body: JSON.stringify({ type, value }) }),
  setRisk: (id: number, isAtRisk: boolean, riskReason?: string) =>
    request<Shipment>(`/shipments/${id}/risk`, {
      method: "POST",
      body: JSON.stringify({ is_at_risk: isAtRisk, risk_reason: riskReason ?? null }),
    }),
}

// --- tracking ---

export const trackingApi = {
  track: (reference: string) => request<TrackingResult>(`/tracking/${encodeURIComponent(reference)}`),
}

// --- meta ---

export const metaApi = {
  stages: () => request<{ stages: StageMeta[] }>("/meta/stages"),
}
