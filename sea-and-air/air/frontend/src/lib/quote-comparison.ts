type ComparableQuote = {
  id: number
  is_current: boolean
  currency: string
  total: string
}

type QuoteStatus = "draft" | "sent" | "accepted" | "expired" | "rejected"

export function prepareQuoteComparison<T extends ComparableQuote>(offers: T[]) {
  const quotes = offers
    .filter((quote) => quote.is_current)
    .toSorted((a, b) => a.currency.localeCompare(b.currency) || amount(a.total) - amount(b.total) || a.id - b.id)
  const currencies = new Set(quotes.map((quote) => quote.currency))
  return { quotes, lowestQuoteId: currencies.size === 1 && quotes.length ? quotes[0].id : null }
}

export function manualSubtotal(items: { amount: string }[]) {
  return items.reduce((total, item) => total + (Number.isFinite(Number(item.amount)) ? Number(item.amount) : 0), 0)
}

export function quoteReference(quote: { id: number; root_quote_id: number | null; revision_number: number }) {
  return `Q-${quote.root_quote_id ?? quote.id} Rev ${quote.revision_number}`
}

export function effectiveQuoteStatus(quote: { status: QuoteStatus; valid_until: string }, now = new Date()): QuoteStatus {
  const localToday = new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10)
  return (quote.status === "draft" || quote.status === "sent") && quote.valid_until < localToday ? "expired" : quote.status
}

function amount(value: string) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : Number.POSITIVE_INFINITY
}
