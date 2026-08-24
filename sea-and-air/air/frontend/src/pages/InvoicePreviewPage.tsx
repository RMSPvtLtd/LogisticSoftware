import { useMemo, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"
import { ArrowLeft, Receipt } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingState, ErrorState } from "@/components/shared/States"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAsync } from "@/hooks/useAsync"
import { ApiError, companiesApi, customersApi, inquiriesApi, invoicesApi, quotesApi, shipmentsApi } from "@/lib/api/client"
import { formatMoney } from "@/lib/format"

const KIND_LABEL: Record<string, string> = {
  freight: "Freight",
  documentation: "Documentation",
  customs: "Customs",
  pickup: "Pickup",
  handling: "Handling",
  other: "Other",
}

// Everything shown here is exactly what create_invoice_from_quote will
// snapshot server-side -- fetched directly from the quote/inquiry/shipment
// rather than a separate "preview" endpoint, since nothing here is computed
// differently at creation time. The only field ops actually chooses is the
// billing entity; the rest is read-only review before committing.
export function InvoicePreviewPage() {
  const { id } = useParams<{ id: string }>()
  const shipmentId = Number(id)
  const navigate = useNavigate()

  const shipment = useAsync(() => shipmentsApi.get(shipmentId), [shipmentId])
  const quote = useAsync(
    () => (shipment.data?.quote_id ? quotesApi.get(shipment.data.quote_id) : Promise.resolve(null)),
    [shipment.data?.quote_id],
  )
  const inquiry = useAsync(
    () => (shipment.data ? inquiriesApi.get(shipment.data.inquiry_id) : Promise.resolve(null)),
    [shipment.data?.inquiry_id],
  )
  const customer = useAsync(
    () => (shipment.data ? customersApi.get(shipment.data.customer_id) : Promise.resolve(null)),
    [shipment.data?.customer_id],
  )
  const companies = useAsync(() => companiesApi.list(), [])

  const [companyId, setCompanyId] = useState<string>("")
  const [note, setNote] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const defaultCompanyId = useMemo(() => {
    const list = companies.data ?? []
    return String((list.find((c) => c.is_default) ?? list[0])?.id ?? "")
  }, [companies.data])
  const selectedCompanyId = companyId || defaultCompanyId

  const loading = shipment.loading || quote.loading || inquiry.loading || customer.loading
  const error = shipment.error ?? quote.error ?? inquiry.error ?? customer.error

  if (loading) return <LoadingState rows={6} />
  if (error || !shipment.data) return <ErrorState message={error ?? "Shipment not found."} onRetry={shipment.reload} />
  if (!quote.data) {
    return <ErrorState message="This shipment has no accepted quote to invoice." onRetry={shipment.reload} />
  }
  if (quote.data.invoice_id) {
    return <ErrorState message="This quote already has an invoice." onRetry={() => navigate(`/invoices/${quote.data!.invoice_id}`)} />
  }

  const q = quote.data
  const s = shipment.data
  const inq = inquiry.data
  const cust = customer.data

  async function handleGenerate() {
    if (!selectedCompanyId) return
    setSubmitting(true)
    try {
      const invoice = await invoicesApi.createFromQuote(q.id, Number(selectedCompanyId))
      await shipmentsApi.invoice(shipmentId, note.trim() || undefined)
      toast.success("Invoice generated")
      navigate(`/invoices/${invoice.id}`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not generate the invoice.")
      setSubmitting(false)
    }
  }

  return (
    <div>
      <Button
        variant="ghost"
        size="sm"
        className="mb-3 -ml-2 gap-1.5 text-muted-foreground"
        onClick={() => navigate(`/shipments/${shipmentId}`)}
      >
        <ArrowLeft size={16} />
        Back to shipment
      </Button>

      <PageHeader
        title="Review invoice"
        description={
          cust && inq ? `${cust.name} · ${inq.origin} → ${inq.destination} · not yet generated` : undefined
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Charges</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Item</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {q.line_items.map((li) => (
                      <TableRow key={li.id}>
                        <TableCell>
                          <span>{KIND_LABEL[li.kind] ?? li.kind}</span>
                          <p className="text-xs text-muted-foreground">{li.description}</p>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{formatMoney(li.final_total, q.currency)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="mt-4 space-y-1.5 border-t border-border pt-4 text-sm">
                <div className="flex justify-between text-muted-foreground">
                  <span>Subtotal</span>
                  <span className="tabular-nums">{formatMoney(q.subtotal, q.currency)}</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>Markup</span>
                  <span className="tabular-nums">{formatMoney(q.markup_amount, q.currency)}</span>
                </div>
                {Number(q.tax_amount) > 0 && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>Tax</span>
                    <span className="tabular-nums">{formatMoney(q.tax_amount, q.currency)}</span>
                  </div>
                )}
                {Number(q.discount_amount) > 0 && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>Discount</span>
                    <span className="tabular-nums">-{formatMoney(q.discount_amount, q.currency)}</span>
                  </div>
                )}
                <div className="flex justify-between border-t border-border pt-2 text-base font-semibold text-foreground">
                  <span>Total</span>
                  <span className="tabular-nums">{formatMoney(q.total, q.currency)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Generate</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <Label>Bill from</Label>
                <Select value={selectedCompanyId} onValueChange={setCompanyId}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder={companies.loading ? "Loading…" : "Select a company"} />
                  </SelectTrigger>
                  <SelectContent>
                    {(companies.data ?? []).map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        {c.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Note (optional)</Label>
                <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Recorded on the shipment's status history" rows={2} />
              </div>
              <Button onClick={handleGenerate} disabled={submitting || !selectedCompanyId} className="w-full gap-1.5">
                <Receipt size={16} />
                {submitting ? "Generating…" : "Generate Invoice"}
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <InfoRow label="Customer" value={cust?.name ?? null} />
              <InfoRowLink label="Originating quote" to={`/quotes/${q.id}`} value={`Quote #${q.id}`} />
              <InfoRowLink label="Job / shipment" to={`/shipments/${s.id}`} value={s.job_number ?? `Shipment #${s.id}`} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Particulars</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <InfoRow label="Job Number" value={s.job_number} />
              <InfoRow label="Incoterm" value={inq?.incoterm ?? null} />
              <InfoRow label="HS Code" value={inq?.hs_code ?? null} />
              <InfoRow label="Pieces" value={inq?.pieces ? String(inq.pieces) : null} />
              <InfoRow label="Gross Weight" value={inq ? `${inq.weight_kg} KGS` : null} />
              <InfoRow label="Volume" value={inq ? `${inq.volume_cbm} CBM` : null} />
              <InfoRow label="Carrier" value={s.carrier} />
              <InfoRow label="Voyage/Flight No" value={s.voyage_flight_number} />
              {inq?.supplier_name && <InfoRow label="Supplier" value={inq.supplier_name} />}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  )
}

function InfoRowLink({ label, to, value }: { label: string; to: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <Link to={to} className="font-medium text-foreground underline outline-none focus-visible:ring-2 focus-visible:ring-ring">
        {value}
      </Link>
    </div>
  )
}
