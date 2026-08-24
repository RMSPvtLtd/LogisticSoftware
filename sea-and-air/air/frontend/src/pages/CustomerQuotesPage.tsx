import { Link } from "react-router-dom"
import { Receipt } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { Badge } from "@/components/ui/badge"
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAsync } from "@/hooks/useAsync"
import { useCustomerAuth } from "@/hooks/useCustomerAuth"
import { customerPortalApi } from "@/lib/api/client"
import { formatDate, formatMoney } from "@/lib/format"
import type { QuoteStatus } from "@/lib/api/types"

const STATUS_LABEL: Record<QuoteStatus, string> = {
  draft: "Draft",
  sent: "Sent",
  accepted: "Accepted",
  expired: "Expired",
  rejected: "Rejected",
}

export function CustomerQuotesPage() {
  const { token } = useCustomerAuth()
  const quotes = useAsync(() => customerPortalApi.quotes(token!), [token])

  return (
    <div>
      <PageHeader title="Quotes" description="Every quote we've prepared for you." />

      {quotes.loading && <LoadingState rows={5} />}
      {!quotes.loading && quotes.error && <ErrorState message={quotes.error} onRetry={quotes.reload} />}
      {!quotes.loading && !quotes.error && (quotes.data?.length ?? 0) === 0 && (
        <EmptyState icon={<Receipt size={32} />} title="No quotes yet" description="Quotes you request will appear here." />
      )}
      {!quotes.loading && !quotes.error && (quotes.data?.length ?? 0) > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Quote</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Total</TableHead>
                <TableHead>Valid Until</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {quotes.data!.map((quote) => (
                <TableRow key={quote.id}>
                  <TableCell className="font-medium tabular-nums">
                    <Link
                      to={`/customer/quotes/${quote.id}`}
                      className="rounded outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      Quote #{quote.root_quote_id ?? quote.id} Rev {quote.revision_number}
                    </Link>
                  </TableCell>
                  <TableCell className="flex flex-wrap items-center gap-1.5">
                    <Badge variant="outline">{STATUS_LABEL[quote.status]}</Badge>
                    {!quote.is_current && <Badge variant="secondary">Superseded</Badge>}
                  </TableCell>
                  <TableCell className="tabular-nums">{formatMoney(quote.total, quote.currency)}</TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground tabular-nums">
                    {formatDate(quote.valid_until)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
