import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"
import { ArrowLeft, CaretRight, Plus, Scales, Trash } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useAsync } from "@/hooks/useAsync"
import { ApiError, inquiriesApi, quotesApi } from "@/lib/api/client"
import { formatDate, formatMoney } from "@/lib/format"
import { manualSubtotal, prepareQuoteComparison } from "@/lib/quote-comparison"
import type { ChargeKind, ManualLineItemInput, Quote } from "@/lib/api/types"

const CHARGE_KINDS: ChargeKind[] = ["freight", "documentation", "customs", "pickup", "handling", "other"]
const emptyLineItem = (): ManualLineItemInput => ({ kind: "freight", description: "", quantity: "1", unit_price: "", amount: "" })

export function InquiryQuotesPage() {
  const { id } = useParams<{ id: string }>()
  const inquiryId = Number(id)
  const navigate = useNavigate()
  const inquiry = useAsync(() => inquiriesApi.get(inquiryId), [inquiryId])
  const offers = useAsync(() => quotesApi.forInquiry(inquiryId), [inquiryId])

  if (inquiry.loading || offers.loading) return <LoadingState rows={4} />
  if (inquiry.error || !inquiry.data) return <ErrorState message={inquiry.error ?? "Inquiry not found."} onRetry={inquiry.reload} />
  if (offers.error) return <ErrorState message={offers.error} onRetry={offers.reload} />

  const { quotes, lowestQuoteId } = prepareQuoteComparison(offers.data ?? [])
  const inq = inquiry.data
  return <div className="mx-auto max-w-6xl">
    <Button variant="ghost" size="sm" className="mb-3 -ml-2 gap-1.5 text-muted-foreground" onClick={() => navigate("/quotes")}><ArrowLeft size={16} /> Quote library</Button>
    <PageHeader title="Compare quotes" description={`${inq.origin} → ${inq.destination} · ${inq.mode.toUpperCase()} · ${inq.cargo_type} · Incoterm ${inq.incoterm}`} action={<ManualQuoteDialog inquiryId={inquiryId} onCreated={offers.reload} />} />
    {quotes.length === 0 ? <EmptyState icon={<Scales size={32} />} title="No quotes yet" description="No rate card matched this lane automatically. Add a manual quote to price it by hand." /> : <><QuoteComparison quotes={quotes} lowestQuoteId={lowestQuoteId} /><PriceBreakdown quotes={quotes} lowestQuoteId={lowestQuoteId} /></>}
  </div>
}

function QuoteComparison({ quotes, lowestQuoteId }: { quotes: Quote[]; lowestQuoteId: number | null }) {
  return <>
    <div className="hidden overflow-x-auto rounded-xl border border-border md:block">
      <table className="w-full min-w-[760px] text-sm"><thead className="bg-muted/40"><tr><th className="h-10 px-3 text-left font-medium">Carrier</th><th className="px-3 text-left font-medium">Quote</th><th className="px-3 text-left font-medium">Source</th><th className="px-3 text-left font-medium">Line items</th><th className="px-3 text-left font-medium">Valid until</th><th className="px-3 text-right font-medium">Total</th><th className="px-3 text-right font-medium">Actions</th></tr></thead>
        <tbody>{quotes.map((quote) => <tr key={quote.id} className="border-t border-border hover:bg-muted/40"><td className="p-3 font-medium">{quote.carrier ?? "Unspecified carrier"}{quote.id === lowestQuoteId && <Badge className="ml-2 bg-status-success-bg text-status-success">Lowest price</Badge>}</td><td className="p-3 tabular-nums">Q-{quote.root_quote_id ?? quote.id} · Rev {quote.revision_number}</td><td className="p-3">{quote.is_manual ? "Manual" : "Rate card"}</td><td className="p-3 text-muted-foreground">{quote.line_items.length} item{quote.line_items.length === 1 ? "" : "s"}</td><td className="p-3 whitespace-nowrap">{formatDate(quote.valid_until)}</td><td className="p-3 text-right font-heading text-base font-semibold tabular-nums">{formatMoney(quote.total, quote.currency)}</td><td className="p-3 text-right"><Button asChild variant="ghost" size="sm"><Link to={`/quotes/${quote.id}`}>Open <CaretRight size={14} /></Link></Button></td></tr>)}</tbody>
      </table>
    </div>
    <ul className="space-y-2 md:hidden" aria-label="Quote comparison">{quotes.map((quote) => <li key={quote.id} className="rounded-xl border border-border p-4"><div className="flex items-start justify-between gap-3"><div><p className="font-medium">{quote.carrier ?? "Unspecified carrier"}</p><p className="text-xs text-muted-foreground">Q-{quote.root_quote_id ?? quote.id} · Rev {quote.revision_number} · {quote.is_manual ? "Manual" : "Rate card"}</p></div>{quote.id === lowestQuoteId && <Badge className="bg-status-success-bg text-status-success">Lowest price</Badge>}</div><div className="mt-4 flex items-end justify-between gap-3"><div className="text-xs text-muted-foreground"><p>{quote.line_items.length} line item{quote.line_items.length === 1 ? "" : "s"}</p><p>Valid until {formatDate(quote.valid_until)}</p></div><div className="text-right"><p className="font-heading text-lg font-semibold tabular-nums">{formatMoney(quote.total, quote.currency)}</p><Button asChild variant="link" size="sm" className="h-auto p-0"><Link to={`/quotes/${quote.id}`}>Open quote</Link></Button></div></div></li>)}</ul>
  </>
}

function PriceBreakdown({ quotes, lowestQuoteId }: { quotes: Quote[]; lowestQuoteId: number | null }) {
  return <section className="mt-7" aria-labelledby="price-breakdown-heading">
    <div className="mb-3"><h2 id="price-breakdown-heading" className="font-heading text-lg font-semibold">Price breakdown</h2><p className="text-sm text-muted-foreground">Actual customer-facing line totals from each current offer.</p></div>
    <div className="grid gap-3 md:grid-flow-col md:auto-cols-[minmax(250px,1fr)] md:overflow-x-auto md:pb-2">{quotes.map((quote) => <article key={quote.id} className="rounded-xl border border-border bg-card p-4"><div className="mb-4 flex items-start justify-between gap-2"><div><h3 className="font-medium">{quote.carrier ?? "Unspecified carrier"}</h3><p className="text-xs text-muted-foreground">{quote.currency} · {quote.is_manual ? "Manual" : "Rate card"}</p></div>{quote.id === lowestQuoteId && <Badge variant="outline">Lowest price</Badge>}</div><dl className="space-y-2">{quote.line_items.map((item) => <div key={item.id} className="flex items-start justify-between gap-3 border-b border-border pb-2 text-sm"><dt><span className="block font-medium">{item.description}</span><span className="capitalize text-xs text-muted-foreground">{item.kind}</span></dt><dd className="shrink-0 tabular-nums">{formatMoney(item.final_total, quote.currency)}</dd></div>)}<div className="flex justify-between gap-3 pt-1 text-sm"><dt className="text-muted-foreground">Subtotal</dt><dd className="tabular-nums">{formatMoney(quote.subtotal, quote.currency)}</dd></div><div className="flex justify-between gap-3 text-sm"><dt className="text-muted-foreground">Markup</dt><dd className="tabular-nums">{formatMoney(quote.markup_amount, quote.currency)}</dd></div>{Number(quote.tax_amount) !== 0 && <div className="flex justify-between gap-3 text-sm"><dt className="text-muted-foreground">Tax</dt><dd className="tabular-nums">{formatMoney(quote.tax_amount, quote.currency)}</dd></div>}{Number(quote.discount_amount) !== 0 && <div className="flex justify-between gap-3 text-sm"><dt className="text-muted-foreground">Discount</dt><dd className="tabular-nums">−{formatMoney(quote.discount_amount, quote.currency)}</dd></div>}<div className="flex justify-between gap-3 border-t border-border pt-3 font-heading font-semibold"><dt>Total</dt><dd className="tabular-nums">{formatMoney(quote.total, quote.currency)}</dd></div></dl></article>)}</div>
  </section>
}

function ManualQuoteDialog({ inquiryId, onCreated }: { inquiryId: number; onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [carrier, setCarrier] = useState("")
  const [currency, setCurrency] = useState("USD")
  const [lineItems, setLineItems] = useState<ManualLineItemInput[]>([emptyLineItem()])
  const enteredSubtotal = manualSubtotal(lineItems)
  const previewCurrency = /^[A-Z]{3}$/.test(currency) ? currency : "USD"
  const valid = Boolean(carrier.trim() && /^[A-Z]{3}$/.test(currency) && lineItems.length && lineItems.every((item) => item.description.trim() && item.quantity.trim() && item.unit_price.trim() && item.amount.trim()))

  function resetForm() { setCarrier(""); setCurrency("USD"); setLineItems([emptyLineItem()]) }
  function updateLine(index: number, patch: Partial<ManualLineItemInput>) { setLineItems((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item)) }
  async function handleSubmit() {
    if (!valid) return
    setSubmitting(true)
    try {
      await quotesApi.createManual({ inquiry_id: inquiryId, carrier: carrier.trim(), currency, line_items: lineItems })
      toast.success("Manual quote added")
      setOpen(false)
      onCreated()
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not create manual quote.")
    } finally { setSubmitting(false) }
  }

  return <Dialog open={open} onOpenChange={(next) => { setOpen(next); if (next) resetForm() }}>
    <DialogTrigger asChild><Button variant="outline" size="sm" className="gap-1.5"><Plus size={14} /> Add manual quote</Button></DialogTrigger>
    <DialogContent className="max-h-[90vh] max-w-6xl overflow-y-auto">
      <DialogHeader><DialogTitle>Add a manual quote</DialogTitle></DialogHeader>
      <p className="text-sm text-muted-foreground">Enter the carrier's base rate. The standard markup is applied by the server after save, exactly as it is for rate-card quotes.</p>
      <div className="grid gap-3 sm:grid-cols-2"><div className="space-y-1.5"><Label htmlFor="manual-carrier">Carrier</Label><Input id="manual-carrier" value={carrier} onChange={(event) => setCarrier(event.target.value)} placeholder="e.g. Qatar Airways Cargo" /></div><div className="space-y-1.5"><Label htmlFor="manual-currency">Currency</Label><Input id="manual-currency" value={currency} maxLength={3} onChange={(event) => setCurrency(event.target.value.toUpperCase().replace(/[^A-Z]/g, ""))} placeholder="USD" /></div></div>
      <div className="space-y-2"><div className="flex items-center justify-between"><Label>Line items</Label><Button type="button" variant="outline" size="sm" onClick={() => setLineItems((items) => [...items, emptyLineItem()])}><Plus size={14} /> Add line</Button></div>{lineItems.map((item, index) => <div key={index} className="grid grid-cols-2 gap-2 rounded-lg border border-border p-3 lg:grid-cols-12"><div className="col-span-2 lg:col-span-2"><Label className="sr-only">Charge kind</Label><Select value={item.kind} onValueChange={(value) => updateLine(index, { kind: value as ChargeKind })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{CHARGE_KINDS.map((kind) => <SelectItem key={kind} value={kind}>{kind}</SelectItem>)}</SelectContent></Select></div><Input aria-label={`Line ${index + 1} description`} placeholder="Description" className="col-span-2 lg:col-span-4" value={item.description} onChange={(event) => updateLine(index, { description: event.target.value })} /><Input aria-label={`Line ${index + 1} quantity`} inputMode="decimal" placeholder="Qty" className="lg:col-span-1" value={item.quantity} onChange={(event) => updateLine(index, { quantity: event.target.value })} /><Input aria-label={`Line ${index + 1} unit price`} inputMode="decimal" placeholder="Unit price" className="lg:col-span-2" value={item.unit_price} onChange={(event) => updateLine(index, { unit_price: event.target.value })} /><Input aria-label={`Line ${index + 1} amount`} inputMode="decimal" placeholder="Base amount" className="lg:col-span-2" value={item.amount} onChange={(event) => updateLine(index, { amount: event.target.value })} /><Button type="button" variant="ghost" size="icon" className="justify-self-end lg:col-span-1" aria-label={`Remove line ${index + 1}`} disabled={lineItems.length <= 1} onClick={() => setLineItems((items) => items.filter((_, itemIndex) => itemIndex !== index))}><Trash size={16} /></Button></div>)}</div>
      <div className="ml-auto w-full max-w-sm rounded-xl border border-border bg-muted/40 p-4"><div className="flex justify-between text-sm"><span className="text-muted-foreground">Entered subtotal</span><span className="font-medium tabular-nums">{formatMoney(String(enteredSubtotal), previewCurrency)}</span></div><div className="mt-2 flex justify-between border-t border-border pt-2"><span className="font-medium">Final quote total</span><span className="text-sm text-muted-foreground">Calculated after save</span></div><p className="mt-2 text-xs text-muted-foreground">No estimated markup is shown because that rate is owned by the server configuration.</p></div>
      <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button onClick={handleSubmit} disabled={!valid || submitting}>{submitting ? "Saving…" : "Add quote"}</Button></DialogFooter>
    </DialogContent>
  </Dialog>
}
