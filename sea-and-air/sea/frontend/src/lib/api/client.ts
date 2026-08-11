// Thin, typed wrapper around the sea backend's tracking API. The browser
// only ever talks to this -- never to sapt.com.pk or any other provider
// directly (Phase 10/13 of the SAPT integration plan).

import type { TrackingResult } from "./types"

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
    } catch {
      // response body wasn't JSON -- fall back to statusText
    }
    throw new ApiError(res.status, detail)
  }

  return res.json() as Promise<T>
}

export const trackingApi = {
  track: (containerNumber: string) =>
    request<TrackingResult>("/tracking", {
      method: "POST",
      body: JSON.stringify({ container_number: containerNumber }),
    }),
}
