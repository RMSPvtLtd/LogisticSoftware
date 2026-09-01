import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"
import { ArrowLeft, CaretRight, Plus, Scales, Trash } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useAsync } from "@/hooks/useAsync"
import { ApiError, inquiriesApi, quotesApi } from "@/lib/api/client"
import { formatDate, formatMoney } from "@/lib/format"
import type { ChargeKind, ManualLineItemInput, Quote } from "@/lib/api/types"

const CHARGE_KINDS: ChargeKind[] = ["freight", "documentation", "customs", "pickup", "handling", "other"]

const EMPTY_LINE_ITEM: ManualLineItemInput = {
  kind: "freight",
  description: "",
  quantity: "1",
  unit_price: "",
  amount: "",
}

export function InquiryQuotesPage() {
  const { id } = useParams<{ id: string }>()
  const inquiryId = Number(id)
  const navigate = useNavigate()

  const inquiry = useAsync(() => inquiriesApi.get(inquiryId), [inquiryId])
  const quotes = useAsync(() => quotesApi.forInquiry(inquiryId), [inquiryId])

  if (inquiry.loading || quotes.loading) return <LoadingState rows={3} />
  if (inquiry.error || !inquiry.data) {
    return <ErrorState message={inquiry.error ?? "Inquiry not found."} onRetry={inquiry.reload} />
  }
  if (quotes.error) return <ErrorState message={quotes.error} onRetry={quotes.reload} />

  const inq = inquiry.data
  const current = (quotes.data ?? [])
    .filter((q) => q.is_current)
    .sort((a, b) => Number(a.total) - Number(b.total))

  return (
    <div className="mx-auto max-w-3xl">
      <Button variant="ghost" size="sm" className="mb-3 -ml-2 gap-1.5 text-muted-foreground" onClick={() => navigate("/shipments")}>
        <ArrowLeft size={16} />
        Shipments
      </Button>

      <PageHeader
        title="Quotes"
        description={`${inq.origin} → ${inq.destination} · ${inq.mode.toUpperCase()} · ${inq.cargo_type} · Incoterm ${inq.incoterm}`}
        action={<ManualQuoteDialog inquiryId={inquiryId} onCreated={quotes.reload} />}
      />

      {current.length === 0 && (
        <EmptyState
          icon={<Scales size={32} />}
          title="No quotes yet"
          description="No rate card matched this lane automatically. Add a manual quote to price it by hand."
        />
      )}

      {current.length > 0 && (
        <div className="space-y-3">
          {current.map((q) => (
            <QuoteCard key={q.id} quote={q} />
          ))}
        </div>
      )}
    </div>
  )
}

function QuoteCard({ quote }: { quote: Quote }) {
  return (
    <Link to={`/quotes/${quote.id}`} className="block outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl">
      <Card className="transition-colors hover:border-primary/50">
        <CardContent className="flex items-center justify-between gap-3 py-4">
          <div>
            <div className="flex items-center gap-2">
              <p className="font-heading text-sm font-semibold text-foreground">{quote.carrier ?? "Unspecified carrier"}</p>
              {quote.is_manual && (
                <Badge variant="outline" className="text-[10px]">
                  Manual
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Q-{quote.root_quote_id ?? quote.id} Rev {quote.revision_number} · Valid until {formatDate(quote.valid_until)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <p className="font-heading text-lg font-semibold tabular-nums text-foreground">
              {formatMoney(quote.total, quote.currency)}
            </p>
            <CaretRight size={16} className="text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}

function ManualQuoteDialog({ inquiryId, onCreated }: { inquiryId: number; onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [carrier, setCarrier] = useState("")
  const [currency, setCurrency] = useState("USD")
  const [lineItems, setLineItems] = useState<ManualLineItemInput[]>([EMPTY_LINE_ITEM])

  function resetForm() {
    setCarrier("")
    setCurrency("USD")
    setLineItems([EMPTY_LINE_ITEM])
  }

  function updateLine(index: number, patch: Partial<ManualLineItemInput>) {
    setLineItems((items) => items.map((li, i) => (i === index ? { ...li, ...patch } : li)))
  }

  const valid =
    carrier.trim() &&
    currency.trim().length === 3 &&
    lineItems.length > 0 &&
    lineItems.every((li) => li.description.trim() && li.quantity.trim() && li.unit_price.trim() && li.amount.trim())

  async function handleSubmit() {
    if (!valid) return
    setSubmitting(true)
    try {
      await quotesApi.createManual({
        inquiry_id: inquiryId,
        carrier: carrier.trim(),
        currency: currency.trim().toUpperCase(),
        line_items: lineItems,
      })
      toast.success("Manual quote added")
      setOpen(false)
      onCreated()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not create manual quote.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (next) resetForm()
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Plus size={14} />
          Add manual quote
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add a manual quote</DialogTitle>
        </DialogHeader>

        <p className="text-sm text-muted-foreground">
          Type in today's rate directly for a carrier -- e.g. when no rate card covers this lane yet, or to add
          another airline's offer by hand. The standard markup is still applied on top, same as every other quote.
        </p>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Carrier</Label>
            <Input value={carrier} onChange={(e) => setCarrier(e.target.value)} placeholder="e.g. Qatar Airways Cargo" />
          </div>
          <div className="space-y-1.5">
            <Label>Currency</Label>
            <Input
              value={currency}
              maxLength={3}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              placeholder="USD"
            />
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Line items</Label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setLineItems((items) => [...items, EMPTY_LINE_ITEM])}
            >
              <Plus size={14} />
            </Button>
          </div>
          {lineItems.map((li, i) => (
            <div key={i} className="grid grid-cols-2 gap-2 rounded-md border border-border p-2 sm:grid-cols-6">
              <Select value={li.kind} onValueChange={(v) => updateLine(i, { kind: v as ChargeKind })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CHARGE_KINDS.map((k) => (
                    <SelectItem key={k} value={k}>
                      {k}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                placeholder="Description"
                className="col-span-2"
                value={li.description}
                onChange={(e) => updateLine(i, { description: e.target.value })}
              />
              <Input
                placeholder="Qty"
                value={li.quantity}
                onChange={(e) => updateLine(i, { quantity: e.target.value })}
              />
              <Input
                placeholder="Unit price"
                value={li.unit_price}
                onChange={(e) => updateLine(i, { unit_price: e.target.value })}
              />
              <Input
                placeholder="Amount"
                value={li.amount}
                onChange={(e) => updateLine(i, { amount: e.target.value })}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="col-span-2 justify-self-start sm:col-span-6"
                disabled={lineItems.length <= 1}
                onClick={() => setLineItems((items) => items.filter((_, idx) => idx !== i))}
              >
                <Trash size={14} className="mr-1" /> Remove line
              </Button>
            </div>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!valid || submitting}>
            {submitting ? "Saving…" : "Add quote"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
