// Locale-aware formatting for the numeric/date strings the API returns.
// Kept in one place so money, weight, and date formatting stay consistent
// across every page (ui-ux-pro-max: number-formatting).

export function formatMoney(value: string, currency: string): string {
  const n = Number(value)
  if (Number.isNaN(n)) return value
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(n)
}

export function formatNumber(value: string, options?: Intl.NumberFormatOptions): string {
  const n = Number(value)
  if (Number.isNaN(n)) return value
  return new Intl.NumberFormat("en-US", options).format(n)
}

export function formatDate(value: string): string {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return new Intl.DateTimeFormat("en-US", { day: "2-digit", month: "short", year: "numeric" }).format(d)
}

export function formatDateTime(value: string): string {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d)
}

export function formatRelativeTime(value: string): string {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const diffMs = d.getTime() - Date.now()
  const diffMinutes = Math.round(diffMs / 60000)
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" })

  const absMin = Math.abs(diffMinutes)
  if (absMin < 60) return rtf.format(diffMinutes, "minute")
  const diffHours = Math.round(diffMinutes / 60)
  if (Math.abs(diffHours) < 24) return rtf.format(diffHours, "hour")
  const diffDays = Math.round(diffHours / 24)
  return rtf.format(diffDays, "day")
}
