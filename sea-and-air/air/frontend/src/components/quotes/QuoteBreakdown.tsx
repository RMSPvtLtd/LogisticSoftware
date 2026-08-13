import { useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { CheckCircle, PaperPlaneTilt, PencilSimpleLine } from "@phosphor-icons/react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { LoadingState, ErrorState } from "@/components/shared/States"
import { useAsync } from "@/hooks/useAsync"
import { inquiriesApi, quotesApi, ApiError } from "@/lib/api/client"
import { formatDate, formatMoney } from "@/lib/format"
import type { Quote, Shipment } from "@/lib/api/types"

const KIND_LABEL: Record<string, string> = {
  freight: "Freight",
  documentation: "Documentation",
  customs: "Customs",
  pickup: "Pickup",
  handling: "Handling",
  other: "Other",
}

export function QuoteBreakdown({ quoteId }: { quoteId: number }) {
  const quote = useAsync(() => quotesApi.get(quoteId), [quoteId])
  const inquiry = useAsync(
    () => (quote.data ? inquiriesApi.get(quote.data.inquiry_id) : Promise.resolve(null)),
    [quote.data?.inquiry_id],
  )
  const [acceptedShipment, setAcceptedShipment] = useState<Shipment | null>(null)

  if (quote.loading) return <LoadingState rows={5} />
  if (quote.error || !quote.data) return <ErrorState message={quote.error ?? "Quote not found."} onRetry={quote.reload} />

  if (acceptedShipment) {
    return <AcceptedPanel shipment={acceptedShipment} />
  }

  return (
    <div className="space-y-6">
      {inquiry.data && (
        <p className="text-sm text-muted-foreground">
          {inquiry.data.origin} → {inquiry.data.destination} · {inquiry.data.mode.toUpperCase()} ·{" "}
          {inquiry.data.cargo_type} · Incoterm {inquiry.data.incoterm}
        </p>
      )}

      <LineItemsCard quote={quote.data} onSaved={quote.reload} />

      <SummaryCard quote={quote.data} />

      <ActionsBar quote={quote.data} onSent={quote.reload} onAccepted={setAcceptedShipment} />
    </div>
  )
}

function LineItemsCard({ quote, onSaved }: { quote: Quote; onSaved: () => void }) {
  const editable = quote.shipment_stage !== "invoice_to_customer"
  const [edits, setEdits] = useState<Record<number, string>>({})
  const [saving, setSaving] = useState(false)

  const dirty = Object.keys(edits).length > 0

  async function handleSave() {
    setSaving(true)
    try {
      await quotesApi.overrideLineItems(
        quote.id,
        Object.entries(edits).map(([lineItemId, finalTotal]) => ({
          line_item_id: Number(lineItemId),
          final_total: finalTotal,
        })),
      )
      toast.success("Line items updated")
      setEdits({})
      onSaved()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save changes.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Price breakdown</CardTitle>
        {editable && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <PencilSimpleLine size={14} />
            Editable until invoiced
          </span>
        )}
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Item</TableHead>
                <TableHead className="text-right">Calculated</TableHead>
                <TableHead className="text-right">Final</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {quote.line_items.map((li) => (
                <TableRow key={li.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span>{KIND_LABEL[li.kind] ?? li.kind}</span>
                      {li.is_manual_override && (
                        <Badge variant="outline" className="text-[10px]">
                          Overridden
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">{li.description}</p>
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-muted-foreground">
                    {formatMoney(li.calculated_total, quote.currency)}
                  </TableCell>
                  <TableCell className="text-right">
                    {editable ? (
                      <Input
                        type="number"
                        step="0.01"
                        defaultValue={li.final_total}
                        className="ml-auto w-28 text-right tabular-nums"
                        onChange={(e) => setEdits((prev) => ({ ...prev, [li.id]: e.target.value }))}
                        aria-label={`Final price for ${li.description}`}
                      />
                    ) : (
                      <span className="tabular-nums font-medium">{formatMoney(li.final_total, quote.currency)}</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {editable && dirty && (
          <div className="mt-3 flex justify-end">
            <Button size="sm" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save overrides"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function SummaryCard({ quote }: { quote: Quote }) {
  return (
    <Card>
      <CardContent className="space-y-1.5 py-5 text-sm">
        <div className="flex justify-between text-muted-foreground">
          <span>Subtotal</span>
          <span className="tabular-nums">{formatMoney(quote.subtotal, quote.currency)}</span>
        </div>
        <div className="flex justify-between text-muted-foreground">
          <span>Markup</span>
          <span className="tabular-nums">{formatMoney(quote.markup_amount, quote.currency)}</span>
        </div>
        <div className="mt-2 flex justify-between border-t border-border pt-2 text-base font-semibold text-foreground">
          <span>Total</span>
          <span className="tabular-nums">{formatMoney(quote.total, quote.currency)}</span>
        </div>
        <p className="pt-1 text-xs text-muted-foreground">Valid until {formatDate(quote.valid_until)}</p>
      </CardContent>
    </Card>
  )
}

function ActionsBar({
  quote,
  onSent,
  onAccepted,
}: {
  quote: Quote
  onSent: () => void
  onAccepted: (shipment: Shipment) => void
}) {
  const [sending, setSending] = useState(false)
  const [accepting, setAccepting] = useState(false)

  const statusLabel = useMemo(
    () => ({ draft: "Draft", sent: "Sent", accepted: "Accepted", expired: "Expired" })[quote.status],
    [quote.status],
  )

  if (quote.status === "expired") {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
        This quote expired on {formatDate(quote.valid_until)} and can no longer be sent or accepted. Generate a
        new quote for this inquiry instead.
      </div>
    )
  }

  if (quote.status === "accepted") {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-status-success/20 bg-status-success/5 px-4 py-3 text-sm text-status-success">
        <CheckCircle size={18} weight="fill" />
        A job has already been opened from this quote.{" "}
        <Link to="/shipments" className="underline">
          View shipments
        </Link>
      </div>
    )
  }

  async function handleSend() {
    setSending(true)
    try {
      await quotesApi.send(quote.id)
      toast.success("Quote marked as sent")
      onSent()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not send quote.")
    } finally {
      setSending(false)
    }
  }

  async function handleAccept() {
    setAccepting(true)
    try {
      const shipment = await quotesApi.accept(quote.id)
      toast.success("Job opened")
      onAccepted(shipment)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not accept quote.")
    } finally {
      setAccepting(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card px-4 py-3">
      <span className="text-sm text-muted-foreground">
        Status: <span className="font-medium text-foreground">{statusLabel}</span>
      </span>
      <div className="flex gap-2">
        {quote.status === "draft" && (
          <Button variant="outline" onClick={handleSend} disabled={sending} className="gap-1.5">
            <PaperPlaneTilt size={16} />
            {sending ? "Sending…" : "Send Quote"}
          </Button>
        )}
        <Button onClick={handleAccept} disabled={accepting} className="gap-1.5">
          <CheckCircle size={16} />
          {accepting ? "Opening job…" : "Open Job"}
        </Button>
      </div>
    </div>
  )
}

function AcceptedPanel({ shipment }: { shipment: Shipment }) {
  const navigate = useNavigate()
  return (
    <Card className="border-status-success/30 bg-status-success/5">
      <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
        <CheckCircle size={40} weight="fill" className="text-status-success" />
        <h2 className="font-heading text-lg font-semibold text-foreground">Job opened</h2>
        <p className="text-sm text-muted-foreground">The shipment has been created with job number</p>
        <p className="font-heading text-2xl font-semibold tabular-nums text-foreground">{shipment.job_number}</p>
        <div className="mt-2 flex gap-2">
          <Button onClick={() => navigate(`/shipments/${shipment.id}`)}>View shipment</Button>
          <Button variant="outline" onClick={() => navigate("/quotes/new")}>
            Create another quote
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
