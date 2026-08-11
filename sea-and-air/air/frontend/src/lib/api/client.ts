// Thin, typed wrapper around the Raaziq backend REST API. Every call goes
// through `request`, so error handling (the backend's centralized
// `{"detail": "..."}` shape) and the base URL are each defined once, not
// repeated at every call site.

import type {
  Area,
  Customer,
  CustomerCreate,
  CustomerLoginResponse,
  CustomerPortalCredentials,
  CustomerShipmentSummary,
  Inquiry,
  InquiryCreate,
  LineItemOverride,
  LoginResponse,
  Quote,
  Shipment,
  ShipmentFilters,
  StageMeta,
  TrackingResult,
  Worker,
  WorkerCreate,
  WorkerQueueItem,
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
  grantPortalAccess: (id: number, payload: CustomerPortalCredentials) =>
    request<Customer>(`/customers/${id}/portal-access`, { method: "POST", body: JSON.stringify(payload) }),
  setPortalActive: (id: number, isActive: boolean) =>
    request<Customer>(`/customers/${id}/portal-access`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    }),
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
  invoice: (id: number, note?: string) =>
    request<Shipment>(`/shipments/${id}/invoice`, { method: "POST", body: JSON.stringify({ note: note || undefined }) }),
}

// --- tracking ---

export const trackingApi = {
  track: (reference: string) => request<TrackingResult>(`/tracking/${encodeURIComponent(reference)}`),
}

// --- meta ---

export const metaApi = {
  stages: () => request<{ stages: StageMeta[] }>("/meta/stages"),
}

// --- auth (worker portal login) ---

export const authApi = {
  login: (username: string, password: string) =>
    request<LoginResponse>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: (token: string) => request<Worker>("/auth/me", { headers: authHeader(token) }),
}

// --- worker portal (requires a worker's own bearer token, not an admin call) ---

export const workerPortalApi = {
  queue: (token: string) => request<WorkerQueueItem[]>("/worker/queue", { headers: authHeader(token) }),
  complete: (token: string, shipmentId: number, note?: string) =>
    request<WorkerQueueItem>(`/worker/shipments/${shipmentId}/complete`, {
      method: "POST",
      headers: authHeader(token),
      body: JSON.stringify({ note: note || undefined }),
    }),
}

function authHeader(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` }
}

// --- customer auth (customer portal login) ---

export const customerAuthApi = {
  login: (username: string, password: string) =>
    request<CustomerLoginResponse>("/customer/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: (token: string) => request<Customer>("/customer/me", { headers: authHeader(token) }),
}

// --- customer portal (requires a customer's own bearer token) ---

export const customerPortalApi = {
  shipments: (token: string, completed?: boolean) =>
    request<CustomerShipmentSummary[]>(`/customer/shipments${qs({ completed })}`, { headers: authHeader(token) }),
  shipment: (token: string, id: number) =>
    request<TrackingResult>(`/customer/shipments/${id}`, { headers: authHeader(token) }),
  quotes: (token: string) => request<Quote[]>("/customer/quotes", { headers: authHeader(token) }),
  quote: (token: string, id: number) => request<Quote>(`/customer/quotes/${id}`, { headers: authHeader(token) }),
}

// --- admin: areas + workers (unauthenticated, same trust level as the rest of the ops API) ---

export const areasApi = {
  list: () => request<Area[]>("/areas"),
}

export const workersApi = {
  list: () => request<Worker[]>("/workers"),
  create: (payload: WorkerCreate) => request<Worker>("/workers", { method: "POST", body: JSON.stringify(payload) }),
  setActive: (id: number, isActive: boolean) =>
    request<Worker>(`/workers/${id}`, { method: "PATCH", body: JSON.stringify({ is_active: isActive }) }),
}
