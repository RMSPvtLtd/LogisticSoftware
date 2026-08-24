import { useParams } from "react-router-dom"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingState, ErrorState } from "@/components/shared/States"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { useAsync } from "@/hooks/useAsync"
import { useCustomerAuth } from "@/hooks/useCustomerAuth"
import { customerPortalApi } from "@/lib/api/client"
import { formatDate, formatMoney } from "@/lib/format"

const KIND_LABEL: Record<string, string> = {
  freight: "Freight",
  documentation: "Documentation",
  customs: "Customs",
  pickup: "Pickup",
  handling: "Handling",
  other: "Other",
}

const STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  sent: "Sent",
  accepted: "Accepted",
  expired: "Expired",
  rejected: "Rejected",
}

export function CustomerQuoteDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { token } = useCustomerAuth()
  const quoteId = Number(id)

  const quote = useAsync(() => customerPortalApi.quote(token!, quoteId), [token, quoteId])

  if (quote.loading) return <LoadingState rows={5} />
  if (quote.error || !quote.data) return <ErrorState message={quote.error ?? "Quote not found."} onRetry={quote.reload} />

  const q = quote.data

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title={`Quote #${q.root_quote_id ?? q.id} Rev ${q.revision_number}`}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{STATUS_LABEL[q.status]}</Badge>
            {!q.is_current && <Badge variant="secondary">Superseded</Badge>}
            <span>Valid until {formatDate(q.valid_until)}</span>
          </span>
        }
      />

      {!q.is_current && (
        <div className="rounded-xl border border-border bg-muted/50 px-4 py-3 text-sm text-muted-foreground">
          This revision has been superseded by a newer quote. Contact us if you need the current version.
        </div>
      )}

      {q.status === "rejected" && q.rejected_reason && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <span className="font-medium">Declined:</span> {q.rejected_reason}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Price breakdown</CardTitle>
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
                    <TableCell className="text-right tabular-nums font-medium">
                      {formatMoney(li.final_total, q.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-1.5 py-5 text-sm">
          <div className="flex justify-between text-muted-foreground">
            <span>Subtotal</span>
            <span className="tabular-nums">{formatMoney(q.subtotal, q.currency)}</span>
          </div>
          <div className="flex justify-between text-muted-foreground">
            <span>Markup</span>
            <span className="tabular-nums">{formatMoney(q.markup_amount, q.currency)}</span>
          </div>
          <div className="mt-2 flex justify-between border-t border-border pt-2 text-base font-semibold text-foreground">
            <span>Total</span>
            <span className="tabular-nums">{formatMoney(q.total, q.currency)}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
