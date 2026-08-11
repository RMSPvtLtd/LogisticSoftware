import { useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Package } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { StageBadge } from "@/components/shared/StageBadge"
import { RiskBadge } from "@/components/shared/RiskBadge"
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { useAsync } from "@/hooks/useAsync"
import { useStages } from "@/hooks/useStages"
import { customersApi, inquiriesApi, shipmentsApi } from "@/lib/api/client"
import { formatDateTime } from "@/lib/format"
import type { ShipmentFilters, ShipmentStage } from "@/lib/api/types"

export function ShipmentListPage() {
  const navigate = useNavigate()
  const { stages } = useStages()
  const [filters, setFilters] = useState<ShipmentFilters>({})

  const shipments = useAsync(() => shipmentsApi.list(filters), [filters.stage, filters.at_risk])
  const customers = useAsync(() => customersApi.list(), [])
  const inquiries = useAsync(() => inquiriesApi.list(), [])

  const customerById = useMemo(
    () => new Map((customers.data ?? []).map((c) => [c.id, c])),
    [customers.data],
  )
  const inquiryById = useMemo(
    () => new Map((inquiries.data ?? []).map((i) => [i.id, i])),
    [inquiries.data],
  )

  const loading = shipments.loading || customers.loading || inquiries.loading
  const error = shipments.error ?? customers.error ?? inquiries.error

  const hasActiveFilters = filters.stage !== undefined || filters.at_risk !== undefined

  return (
    <div>
      <PageHeader
        title="Shipments"
        description="Every job currently moving through the Raaziq network."
        action={
          <Button onClick={() => navigate("/quotes/new")} className="gap-1.5">
            New Quote
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Select
          value={filters.stage ?? "all"}
          onValueChange={(v) => setFilters((f) => ({ ...f, stage: v === "all" ? undefined : (v as ShipmentStage) }))}
        >
          <SelectTrigger className="w-44" aria-label="Filter by stage">
            <SelectValue placeholder="All stages" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All stages</SelectItem>
            {stages.map((s) => (
              <SelectItem key={s.stage} value={s.stage}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={filters.at_risk === undefined ? "all" : String(filters.at_risk)}
          onValueChange={(v) => setFilters((f) => ({ ...f, at_risk: v === "all" ? undefined : v === "true" }))}
        >
          <SelectTrigger className="w-40" aria-label="Filter by risk">
            <SelectValue placeholder="All shipments" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All shipments</SelectItem>
            <SelectItem value="true">At risk only</SelectItem>
            <SelectItem value="false">Not at risk</SelectItem>
          </SelectContent>
        </Select>

        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={() => setFilters({})}>
            Clear filters
          </Button>
        )}
      </div>

      {loading && <LoadingState rows={5} />}
      {!loading && error && <ErrorState message={error} onRetry={shipments.reload} />}
      {!loading && !error && (shipments.data?.length ?? 0) === 0 && (
        <EmptyState
          icon={<Package size={32} />}
          title={hasActiveFilters ? "No shipments match these filters" : "No shipments yet"}
          description={
            hasActiveFilters
              ? "Try clearing a filter to see more results."
              : "Accepted quotes automatically appear here as shipments."
          }
          action={
            hasActiveFilters ? (
              <Button variant="outline" onClick={() => setFilters({})}>
                Clear filters
              </Button>
            ) : undefined
          }
        />
      )}
      {!loading && !error && (shipments.data?.length ?? 0) > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job Number</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Route</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>Last Updated</TableHead>
                <TableHead>Risk</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {shipments.data!.map((shipment) => {
                const customer = customerById.get(shipment.customer_id)
                const inquiry = inquiryById.get(shipment.inquiry_id)
                return (
                  <TableRow
                    key={shipment.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/shipments/${shipment.id}`)}
                  >
                    <TableCell className="font-medium tabular-nums">
                      <Link
                        to={`/shipments/${shipment.id}`}
                        className="rounded outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {shipment.job_number}
                      </Link>
                    </TableCell>
                    <TableCell>{customer?.name ?? "—"}</TableCell>
                    <TableCell className="whitespace-nowrap">
                      {inquiry ? `${inquiry.origin} → ${inquiry.destination}` : "—"}
                    </TableCell>
                    <TableCell>
                      <StageBadge stage={shipment.stage} />
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground tabular-nums">
                      {formatDateTime(shipment.updated_at)}
                    </TableCell>
                    <TableCell>{shipment.is_at_risk && <RiskBadge />}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
