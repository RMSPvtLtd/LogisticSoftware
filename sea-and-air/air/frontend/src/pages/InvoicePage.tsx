import { useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, DownloadSimple } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingState, ErrorState } from "@/components/shared/States"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAsync } from "@/hooks/useAsync"
import { invoicesApi } from "@/lib/api/client"
import { formatDate, formatMoney } from "@/lib/format"

const KIND_LABEL: Record<string, string> = {
  freight: "Freight",
  documentation: "Documentation",
  customs: "Customs",
  pickup: "Pickup",
  handling: "Handling",
  other: "Other",
}

const STATUS_LABEL: Record<string, string> = { draft: "Draft", issued: "Issued", paid: "Paid", cancelled: "Cancelled" }

export function InvoicePage() {
  const { id } = useParams<{ id: string }>()
  const invoiceId = Number(id)
  const navigate = useNavigate()

  const invoice = useAsync(() => invoicesApi.get(invoiceId), [invoiceId])

  if (invoice.loading) return <LoadingState rows={6} />
  if (invoice.error || !invoice.data) {
    return <ErrorState message={invoice.error ?? "Invoice not found."} onRetry={invoice.reload} />
  }

  const inv = invoice.data

  return (
    <div>
      <Button variant="ghost" size="sm" className="mb-3 -ml-2 gap-1.5 text-muted-foreground" onClick={() => navigate("/invoices")}>
        <ArrowLeft size={16} />
        All invoices
      </Button>

      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            {inv.invoice_number}
            <Badge variant="outline">{STATUS_LABEL[inv.status] ?? inv.status}</Badge>
          </span>
        }
        description={`${inv.customer_name_snapshot} · ${inv.origin_snapshot} → ${inv.destination_snapshot} · Issued ${formatDate(inv.issued_date)}`}
        action={
          <a href={invoicesApi.pdfUrl(inv.id)} target="_blank" rel="noreferrer">
            <Button variant="outline" className="gap-1.5">
              <DownloadSimple size={16} />
              Download PDF
            </Button>
          </a>
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
                    {inv.line_items.map((li) => (
                      <TableRow key={li.id}>
                        <TableCell>
                          <span>{KIND_LABEL[li.kind] ?? li.kind}</span>
                          <p className="text-xs text-muted-foreground">{li.description}</p>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{formatMoney(li.amount, inv.currency)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="mt-4 space-y-1.5 border-t border-border pt-4 text-sm">
                <div className="flex justify-between text-muted-foreground">
                  <span>Subtotal</span>
                  <span className="tabular-nums">{formatMoney(inv.subtotal, inv.currency)}</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>Markup</span>
                  <span className="tabular-nums">{formatMoney(inv.markup_amount, inv.currency)}</span>
                </div>
                {Number(inv.tax_amount) > 0 && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>Tax</span>
                    <span className="tabular-nums">{formatMoney(inv.tax_amount, inv.currency)}</span>
                  </div>
                )}
                {Number(inv.discount_amount) > 0 && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>Discount</span>
                    <span className="tabular-nums">-{formatMoney(inv.discount_amount, inv.currency)}</span>
                  </div>
                )}
                <div className="flex justify-between border-t border-border pt-2 text-base font-semibold text-foreground">
                  <span>Total</span>
                  <span className="tabular-nums">{formatMoney(inv.total, inv.currency)}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Particulars</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <InfoRow label="Job Number" value={inv.job_number_snapshot} />
              <InfoRow label="Incoterm" value={inv.incoterm_snapshot} />
              <InfoRow label="HS Code" value={inv.hs_code_snapshot} />
              <InfoRow label="Pieces" value={inv.pieces_snapshot ? String(inv.pieces_snapshot) : null} />
              <InfoRow label="Gross Weight" value={`${inv.weight_kg_snapshot} KGS`} />
              <InfoRow label="Chargeable Weight" value={`${inv.chargeable_weight_kg_snapshot} KGS`} />
              <InfoRow label="Carrier" value={inv.carrier_snapshot} />
              <InfoRow label="Voyage/Flight No" value={inv.voyage_flight_number_snapshot} />
              {inv.supplier_name_snapshot && <InfoRow label="Supplier" value={inv.supplier_name_snapshot} />}
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
