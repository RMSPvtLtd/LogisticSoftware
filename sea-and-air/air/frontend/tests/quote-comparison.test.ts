import assert from "node:assert/strict"
import test from "node:test"

import { manualSubtotal, prepareQuoteComparison } from "../src/lib/quote-comparison.ts"

test("comparison keeps current offers, sorts by real totals, and names one lowest price", () => {
  const quotes = [
    { id: 3, is_current: false, currency: "USD", total: "80.00" },
    { id: 2, is_current: true, currency: "USD", total: "125.00" },
    { id: 1, is_current: true, currency: "USD", total: "100.00" },
  ]

  assert.deepEqual(prepareQuoteComparison(quotes), {
    quotes: [quotes[2], quotes[1]],
    lowestQuoteId: 1,
  })
})

test("comparison does not claim a lowest price across currencies", () => {
  const quotes = [
    { id: 1, is_current: true, currency: "USD", total: "100.00" },
    { id: 2, is_current: true, currency: "PKR", total: "50.00" },
  ]

  assert.equal(prepareQuoteComparison(quotes).lowestQuoteId, null)
})

test("manual subtotal uses only finite entered amounts", () => {
  assert.equal(manualSubtotal([{ amount: "100.25" }, { amount: "20" }, { amount: "" }, { amount: "invalid" }]), 120.25)
})
