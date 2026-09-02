import { useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { MagnifyingGlass, Package, Trash, X } from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/States"
import { PageHeader } from "@/components/shared/PageHeader"
import { RiskBadge } from "@/components/shared/RiskBadge"
import { StageBadge } from "@/components/shared/StageBadge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAsync } from "@/hooks/useAsync"
import { useStages } from "@/hooks/useStages"
import { ApiError, customersApi, inquiriesApi, shipmentsApi } from "@/lib/api/client"
import { attentionText, formatWaitingAge, quickViewCounts, stageEnteredAt } from "@/lib/shipment-operations"
import { filterShipments, parseShipmentQuery } from "@/lib/shipment-filters"
import type { Priority } from "@/lib/api/types"

type QuickView = "all" | "attention" | "atRisk" | "onHold" | "highPriority" | "readyToInvoice" | "completed"

const QUICK_VIEWS: { id: QuickView; label: string }[] = [
  { id: "all", label: "All" }, { id: "attention", label: "Needs attention" }, { id: "atRisk", label: "At risk" },
  { id: "onHold", label: "On hold" }, { id: "highPriority", label: "High priority" },
  { id: "readyToInvoice", label: "Ready to invoice" }, { id: "completed", label: "Completed" },
]

function matchesQuickView(view: QuickView, shipment: { stage: string; is_at_risk: boolean; is_on_hold: boolean; priority: string }) {
  if (view === "attention") return shipment.is_at_risk || shipment.is_on_hold
  if (view === "atRisk") return shipment.is_at_risk
  if (view === "onHold") return shipment.is_on_hold
  if (view === "highPriority") return shipment.priority === "high"
  if (view === "readyToInvoice") return shipment.stage === "arrival"
  if (view === "completed") return shipment.stage === "invoice_to_customer"
  return true
}

export function ShipmentListPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { stages } = useStages()
  const queryString = searchParams.toString()
  const query = useMemo(() => parseShipmentQuery(new URLSearchParams(queryString)), [queryString])
  const [quickView, setQuickView] = useState<QuickView>("all")
  const [priority, setPriority] = useState<Priority | "all">("all")
  const [customerId, setCustomerId] = useState("all")
  const [route, setRoute] = useState("all")
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; label: string } | null>(null)
  const [deleting, setDeleting] = useState(false)
  const shipments = useAsync(() => shipmentsApi.list(), [])
  const customers = useAsync(() => customersApi.list(), [])
  const inquiries = useAsync(() => inquiriesApi.list(), [])
  const customerById = useMemo(() => new Map((customers.data ?? []).map((customer) => [customer.id, customer])), [customers.data])
  const inquiryById = useMemo(() => new Map((inquiries.data ?? []).map((inquiry) => [inquiry.id, inquiry])), [inquiries.data])
  const routeOptions = useMemo(
    () => [...new Map((inquiries.data ?? []).map((inquiry) => [`${inquiry.origin}\u0000${inquiry.destination}`, `${inquiry.origin} → ${inquiry.destination}`])).entries()],
    [inquiries.data],
  )
  const counts = useMemo(() => quickViewCounts(shipments.data ?? []), [shipments.data])
  const visibleShipments = useMemo(() => {
    const routeMatch = route === "all" ? null : route.split("\u0000")
    return filterShipments(shipments.data ?? [], customers.data ?? [], inquiries.data ?? [], query).filter((shipment) => {
      const inquiry = inquiryById.get(shipment.inquiry_id)
      return matchesQuickView(quickView, shipment)
        && (priority === "all" || shipment.priority === priority)
        && (customerId === "all" || shipment.customer_id === Number(customerId))
        && (!routeMatch || (inquiry?.origin === routeMatch[0] && inquiry.destination === routeMatch[1]))
    })
  }, [customerId, customers.data, inquiries.data, inquiryById, priority, query, quickView, route, shipments.data])
  const loading = shipments.loading || customers.loading || inquiries.loading
  const error = shipments.error ?? customers.error ?? inquiries.error
  const hasFilters = quickView !== "all" || priority !== "all" || customerId !== "all" || route !== "all" || queryString !== ""

  function setQuery(name: string, value?: string) {
    const next = new URLSearchParams(queryString)
    if (value) next.set(name, value)
    else next.delete(name)
    setSearchParams(next)
  }

  function clearFilters() {
    setQuickView("all")
    setPriority("all")
    setCustomerId("all")
    setRoute("all")
    setSearchParams({})
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await shipmentsApi.remove(deleteTarget.id)
      toast.success(`${deleteTarget.label} deleted`)
      setDeleteTarget(null)
      shipments.reload()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete shipment.")
    } finally {
      setDeleting(false)
    }
  }

  return <div>
    <PageHeader title="Shipments" description="Exception-first view of every job moving through the Raaziq network." action={<Button onClick={() => navigate("/quotes/new")}>New Quote</Button>} />
    <div className="mb-4 flex flex-wrap gap-2" aria-label="Shipment quick views">
      {QUICK_VIEWS.map((view) => <Button key={view.id} variant={quickView === view.id ? "secondary" : "ghost"} size="sm" onClick={() => setQuickView(view.id)} aria-pressed={quickView === view.id} className="gap-1.5">{view.label} <span className="tabular-nums text-muted-foreground">{counts[view.id]}</span></Button>)}
    </div>
    <div className="mb-4 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
      <div className="relative">
        <MagnifyingGlass size={17} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input value={query.search} onChange={(event) => setQuery("search", event.target.value.trim() || undefined)} placeholder="Search job, customer, route, or reference…" aria-label="Search shipments" className="pl-9 pr-9" />
        {query.search && <Button variant="ghost" size="icon-sm" className="absolute top-1/2 right-1 -translate-y-1/2" onClick={() => setQuery("search")} aria-label="Clear shipment search"><X size={15} /></Button>}
      </div>
      <p className="self-center text-sm text-muted-foreground"><span className="font-medium text-foreground tabular-nums">{visibleShipments.length}</span> result{visibleShipments.length === 1 ? "" : "s"}</p>
    </div>
    <div className="mb-5 flex flex-wrap items-center gap-2">
      <Select value={query.mode ?? "all"} onValueChange={(value) => setQuery("mode", value === "all" ? undefined : value)}><SelectTrigger className="w-32" aria-label="Filter by mode"><SelectValue placeholder="Mode" /></SelectTrigger><SelectContent><SelectItem value="all">All modes</SelectItem><SelectItem value="air">Air</SelectItem><SelectItem value="sea">Sea</SelectItem><SelectItem value="road">Road</SelectItem></SelectContent></Select>
      <Select value={query.stages.length === 1 ? query.stages[0] : "all"} onValueChange={(value) => setQuery("stage", value === "all" ? undefined : value)}><SelectTrigger className="w-44" aria-label="Filter by stage"><SelectValue placeholder="Stage" /></SelectTrigger><SelectContent><SelectItem value="all">All stages</SelectItem>{stages.map((stage) => <SelectItem key={stage.stage} value={stage.stage}>{stage.label}</SelectItem>)}</SelectContent></Select>
      <Select value={customerId} onValueChange={setCustomerId}><SelectTrigger className="w-44" aria-label="Filter by customer"><SelectValue placeholder="Customer" /></SelectTrigger><SelectContent><SelectItem value="all">All customers</SelectItem>{(customers.data ?? []).map((customer) => <SelectItem key={customer.id} value={String(customer.id)}>{customer.name}</SelectItem>)}</SelectContent></Select>
      <Select value={route} onValueChange={setRoute}><SelectTrigger className="w-44" aria-label="Filter by route"><SelectValue placeholder="Route" /></SelectTrigger><SelectContent><SelectItem value="all">All routes</SelectItem>{routeOptions.map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}</SelectContent></Select>
      <Select value={priority} onValueChange={(value) => setPriority(value as Priority | "all")}><SelectTrigger className="w-36" aria-label="Filter by priority"><SelectValue placeholder="Priority" /></SelectTrigger><SelectContent><SelectItem value="all">All priorities</SelectItem><SelectItem value="low">Low</SelectItem><SelectItem value="medium">Medium</SelectItem><SelectItem value="high">High</SelectItem></SelectContent></Select>
      {hasFilters && <Button variant="ghost" size="sm" onClick={clearFilters}>Clear filters</Button>}
    </div>
    {loading && <LoadingState rows={6} />}
    {!loading && error && <ErrorState message={error} onRetry={shipments.reload} />}
    {!loading && !error && visibleShipments.length === 0 && <EmptyState icon={<Package size={32} />} title="No shipments match this view" description="Try another quick view or clear a filter." action={hasFilters ? <Button variant="outline" onClick={clearFilters}>Clear filters</Button> : undefined} />}
    {!loading && !error && visibleShipments.length > 0 && <ShipmentRecords shipments={visibleShipments} customerById={customerById} inquiryById={inquiryById} onDelete={setDeleteTarget} />}
    <Dialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && !deleting && setDeleteTarget(null)}><DialogContent><DialogHeader><DialogTitle>Delete shipment {deleteTarget?.label}?</DialogTitle><DialogDescription>This permanently removes the shipment and permitted related records. Financial-record safeguards remain enforced by the server.</DialogDescription></DialogHeader><DialogFooter><Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button><Button variant="destructive" onClick={handleDelete} disabled={deleting}>{deleting ? "Deleting…" : "Delete shipment"}</Button></DialogFooter></DialogContent></Dialog>
  </div>
}

type ShipmentRecordsProps = { shipments: Awaited<ReturnType<typeof shipmentsApi.list>>; customerById: Map<number, { name: string }>; inquiryById: Map<number, { origin: string; destination: string }>; onDelete: (target: { id: number; label: string }) => void }

function ShipmentRecords({ shipments, customerById, inquiryById, onDelete }: ShipmentRecordsProps) {
  const record = (shipment: ShipmentRecordsProps["shipments"][number]) => {
    const customer = customerById.get(shipment.customer_id)
    const inquiry = inquiryById.get(shipment.inquiry_id)
    const label = shipment.job_number ?? `Inquiry #${shipment.inquiry_id}`
    const waiting = formatWaitingAge(stageEnteredAt(shipment.stage, shipment.status_events))
    return { customer, inquiry, label, waiting }
  }
  return <>
    <div className="hidden overflow-x-auto rounded-xl border border-border md:block"><Table><TableHeader className="sticky top-0 z-10 bg-background shadow-[0_1px_0_hsl(var(--border))]"><TableRow><TableHead>Job</TableHead><TableHead>Customer</TableHead><TableHead>Route</TableHead><TableHead>Stage</TableHead><TableHead>Waiting</TableHead><TableHead>Attention</TableHead><TableHead className="w-10"><span className="sr-only">Actions</span></TableHead></TableRow></TableHeader><TableBody>{shipments.map((shipment) => { const { customer, inquiry, label, waiting } = record(shipment); return <TableRow key={shipment.id}><TableCell className="font-medium tabular-nums"><Link to={`/shipments/${shipment.id}`} className="rounded hover:underline focus-visible:ring-2 focus-visible:ring-ring">{label}</Link></TableCell><TableCell>{customer?.name ?? "—"}</TableCell><TableCell>{inquiry ? `${inquiry.origin} → ${inquiry.destination}` : "—"}</TableCell><TableCell><StageBadge stage={shipment.stage} /></TableCell><TableCell className="tabular-nums text-muted-foreground">{waiting}</TableCell><TableCell>{attentionText(shipment) ? <div className="flex flex-wrap gap-1">{shipment.is_on_hold && <span className="rounded bg-status-warning-bg px-1.5 py-0.5 text-xs font-medium text-status-warning">On hold</span>}{shipment.is_at_risk && <RiskBadge />}</div> : <span className="text-muted-foreground">—</span>}</TableCell><TableCell><Button variant="ghost" size="icon" aria-label={`Delete ${label}`} onClick={() => onDelete({ id: shipment.id, label })} className="text-destructive hover:text-destructive"><Trash size={16} /></Button></TableCell></TableRow>})}</TableBody></Table></div>
    <ul className="space-y-2 md:hidden" aria-label="Shipment records">{shipments.map((shipment) => { const { customer, inquiry, label, waiting } = record(shipment); return <li key={shipment.id} className="rounded-xl border border-border p-3"><div className="flex items-start justify-between gap-3"><div><Link to={`/shipments/${shipment.id}`} className="font-medium tabular-nums hover:underline focus-visible:ring-2 focus-visible:ring-ring">{label}</Link><p className="mt-0.5 text-sm text-muted-foreground">{customer?.name ?? "—"}</p></div><StageBadge stage={shipment.stage} /></div><p className="mt-3 text-sm">{inquiry ? `${inquiry.origin} → ${inquiry.destination}` : "Route unavailable"}</p><div className="mt-3 flex items-center justify-between text-xs text-muted-foreground"><span>Waiting {waiting}</span><span>{attentionText(shipment) ?? "No attention flags"}</span></div></li>})}</ul>
  </>
}
