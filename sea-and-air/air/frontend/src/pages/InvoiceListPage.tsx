import { useNavigate } from "react-router-dom"
import { Link } from "react-router-dom"
import { Receipt } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAsync } from "@/hooks/useAsync"
import { invoicesApi } from "@/lib/api/client"
import { formatDate, formatMoney } from "@/lib/format"

const STATUS_LABEL: Record<string, string> = { draft: "Draft", issued: "Issued", paid: "Paid", cancelled: "Cancelled" }

export function InvoiceListPage() {
  const navigate = useNavigate()
  const invoices = useAsync(() => invoicesApi.list(), [])

  return (
    <div>
      <PageHeader title="Invoices" description="Every invoice generated from an accepted quote." />

      {invoices.loading && <LoadingState rows={5} />}
      {!invoices.loading && invoices.error && <ErrorState message={invoices.error} onRetry={invoices.reload} />}
      {!invoices.loading && !invoices.error && (invoices.data?.length ?? 0) === 0 && (
        <EmptyState
          icon={<Receipt size={32} />}
          title="No invoices yet"
          description="Invoices appear here once ops creates one from an accepted quote."
        />
      )}
      {!invoices.loading && !invoices.error && (invoices.data?.length ?? 0) > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice No</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Route</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Date</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoices.data!.map((invoice) => (
                <TableRow
                  key={invoice.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/invoices/${invoice.id}`)}
                >
                  <TableCell className="font-medium tabular-nums">
                    <Link
                      to={`/invoices/${invoice.id}`}
                      className="rounded outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {invoice.invoice_number}
                    </Link>
                  </TableCell>
                  <TableCell>{invoice.customer_name_snapshot}</TableCell>
                  <TableCell className="whitespace-nowrap">
                    {invoice.origin_snapshot} → {invoice.destination_snapshot}
                  </TableCell>
                  <TableCell>
                    <Badge variant={invoice.status === "cancelled" ? "secondary" : "outline"}>
                      {STATUS_LABEL[invoice.status] ?? invoice.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground tabular-nums">
                    {formatDate(invoice.issued_date)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-medium">
                    {formatMoney(invoice.total, invoice.currency)}
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
