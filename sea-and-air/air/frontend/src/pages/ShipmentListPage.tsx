import { useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { CaretDown, CaretUp, Package } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { StageBadge } from "@/components/shared/StageBadge"
import { RiskBadge } from "@/components/shared/RiskBadge"
import { ErrorState, EmptyState, TableSkeleton } from "@/components/shared/States"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { useAsync } from "@/hooks/useAsync"
import { useStages } from "@/hooks/useStages"
import { customersApi, inquiriesApi, shipmentsApi } from "@/lib/api/client"
import { formatDateTime } from "@/lib/format"
import type { ShipmentFilters, ShipmentStage } from "@/lib/api/types"

type ListTab = "active" | "completed"
type SortKey = "job_number" | "updated_at"

export function ShipmentListPage() {
  const navigate = useNavigate()
  const { stages } = useStages()
  const [tab, setTab] = useState<ListTab>("active")
  const [filters, setFilters] = useState<ShipmentFilters>({})
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "updated_at", dir: "desc" })

  function toggleSort(key: SortKey) {
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }))
  }

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

  const visibleShipments = useMemo(() => {
    const filtered = (shipments.data ?? []).filter((s) =>
      tab === "completed" ? s.stage === "invoice_to_customer" : s.stage !== "invoice_to_customer",
    )
    const sorted = [...filtered].sort((a, b) => {
      const av = sort.key === "job_number" ? (a.job_number ?? "") : a.updated_at
      const bv = sort.key === "job_number" ? (b.job_number ?? "") : b.updated_at
      const cmp = av < bv ? -1 : av > bv ? 1 : 0
      return sort.dir === "asc" ? cmp : -cmp
    })
    return sorted
  }, [shipments.data, tab, sort])

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

      <Tabs value={tab} onValueChange={(v) => setTab(v as ListTab)} className="mb-4">
        <TabsList>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
        </TabsList>
      </Tabs>

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
            {stages
              .filter((s) => s.stage !== "invoice_to_customer")
              .map((s) => (
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

      {loading && <TableSkeleton columns={6} rows={5} />}
      {!loading && error && <ErrorState message={error} onRetry={shipments.reload} />}
      {!loading && !error && visibleShipments.length === 0 && (
        <EmptyState
          icon={<Package size={32} />}
          title={
            tab === "completed"
              ? "No completed shipments yet"
              : hasActiveFilters
                ? "No shipments match these filters"
                : "No shipments yet"
          }
          description={
            tab === "completed"
              ? "Shipments appear here once they've been invoiced."
              : hasActiveFilters
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
      {!loading && !error && visibleShipments.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableHead label="Job Number" sortKey="job_number" sort={sort} onSort={toggleSort} />
                <TableHead>Customer</TableHead>
                <TableHead>Route</TableHead>
                <TableHead>Stage</TableHead>
                <SortableHead label="Last Updated" sortKey="updated_at" sort={sort} onSort={toggleSort} />
                <TableHead>Risk</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleShipments.map((shipment) => {
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

function SortableHead({
  label,
  sortKey,
  sort,
  onSort,
}: {
  label: string
  sortKey: SortKey
  sort: { key: SortKey; dir: "asc" | "desc" }
  onSort: (key: SortKey) => void
}) {
  const active = sort.key === sortKey
  return (
    <TableHead>
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className="flex items-center gap-1 text-foreground transition-colors duration-[var(--motion-fast)] hover:text-accent-foreground"
      >
        {label}
        {active ? (
          sort.dir === "asc" ? (
            <CaretUp size={12} weight="bold" />
          ) : (
            <CaretDown size={12} weight="bold" />
          )
        ) : (
          <CaretDown size={12} className="opacity-0 group-hover:opacity-40" />
        )}
      </button>
    </TableHead>
  )
}
