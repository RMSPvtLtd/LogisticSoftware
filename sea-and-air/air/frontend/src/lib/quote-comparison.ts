type ComparableQuote = {
  id: number
  is_current: boolean
  currency: string
  total: string
}

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

function amount(value: string) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : Number.POSITIVE_INFINITY
}
