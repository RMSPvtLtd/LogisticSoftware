import { useMemo } from "react"
import { Link } from "react-router-dom"
import { ArrowUpRight, Clock, MapPin, Package, Plus, ShieldWarning, Snowflake, UserCircle } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { StageBadge } from "@/components/shared/StageBadge"
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAsync } from "@/hooks/useAsync"
import { useStages } from "@/hooks/useStages"
import { customersApi, inquiriesApi, shipmentsApi } from "@/lib/api/client"
import { deriveOverviewData, formatWaiting } from "@/lib/overview"

const metricCards = [
  { key: "active", label: "Active shipments", icon: Package, tone: "text-accent-foreground" },
  { key: "atRisk", label: "At risk", icon: ShieldWarning, tone: "text-destructive" },
  { key: "onHold", label: "On hold", icon: Snowflake, tone: "text-status-warning" },
  { key: "readyToInvoice", label: "Ready to invoice", icon: ArrowUpRight, tone: "text-status-success" },
] as const

function formatMode(mode: string) {
  return mode.charAt(0).toUpperCase() + mode.slice(1)
}

function SchematicNetwork({ lanes }: { lanes: ReturnType<typeof deriveOverviewData>["lanes"] }) {
  if (lanes.length === 0) {
    return <EmptyState icon={<MapPin size={28} />} title="No active lanes" description="Active shipment routes will appear here." />
  }

  const visibleLanes = lanes.slice(0, 6)
  const height = Math.max(220, visibleLanes.length * 54 + 30)

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border bg-muted/30 p-3">
        <svg
          viewBox={`0 0 640 ${height}`}
          className="h-auto max-h-80 w-full"
          role="img"
          aria-labelledby="network-title network-description"
        >
          <title id="network-title">Schematic active shipment route network</title>
          <desc id="network-description">A non-geographic diagram of active origin-to-destination lanes.</desc>
          {visibleLanes.map((lane, index) => {
            const y = 28 + index * 54
            return (
              <g key={lane.key}>
                <line x1="150" y1={y} x2="490" y2={y} stroke="var(--accent-foreground)" strokeWidth="3" strokeLinecap="round" opacity="0.75" />
                <circle cx="150" cy={y} r="7" fill="var(--card)" stroke="var(--accent-foreground)" strokeWidth="3" />
                <circle cx="490" cy={y} r="7" fill="var(--card)" stroke="var(--accent-foreground)" strokeWidth="3" />
                <text x="132" y={y - 13} textAnchor="end" fill="var(--foreground)" fontSize="14" fontWeight="600">{lane.origin}</text>
                <text x="508" y={y - 13} fill="var(--foreground)" fontSize="14" fontWeight="600">{lane.destination}</text>
                <text x="320" y={y + 5} textAnchor="middle" fill="var(--muted-foreground)" fontSize="12">{lane.active} active</text>
              </g>
            )
          })}
        </svg>
      </div>
      <ul className="grid gap-2 sm:grid-cols-2" aria-label="Active lane details">
        {visibleLanes.map((lane) => (
          <li key={lane.key} className="rounded-lg border border-border bg-background px-3 py-2.5">
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium">{lane.origin} <span className="text-muted-foreground">→</span> {lane.destination}</span>
              <Badge variant="secondary">{formatMode(lane.mode)}</Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {lane.active} active{lane.atRisk ? ` · ${lane.atRisk} at risk` : ""}{lane.onHold ? ` · ${lane.onHold} on hold` : ""}
            </p>
          </li>
        ))}
      </ul>
      {lanes.length > visibleLanes.length && <p className="text-xs text-muted-foreground">Showing the {visibleLanes.length} busiest lanes of {lanes.length} active lanes.</p>}
    </div>
  )
}

export function OverviewPage() {
  const { stages, loading: stagesLoading, labelFor } = useStages()
  const shipments = useAsync(() => shipmentsApi.list(), [])
  const customers = useAsync(() => customersApi.list(), [])
  const inquiries = useAsync(() => inquiriesApi.list(), [])
  const data = useMemo(
    () => deriveOverviewData(shipments.data ?? [], customers.data ?? [], inquiries.data ?? [], stages),
    [shipments.data, customers.data, inquiries.data, stages],
  )
  const loading = shipments.loading || customers.loading || inquiries.loading || stagesLoading
  const error = shipments.error ?? customers.error ?? inquiries.error

  if (loading) return <LoadingState rows={6} />
  if (error) return <ErrorState message={error} onRetry={shipments.reload} />

  return (
    <div className="space-y-6">
      <PageHeader
        title="Control Tower"
        description="A truthful view of what is moving, waiting, and ready for the next action."
        action={
          <Button asChild className="gap-1.5">
            <Link to="/quotes/new"><Plus size={16} /> New Quote</Link>
          </Button>
        }
      />

      <section aria-label="Shipment metrics" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metricCards.map(({ key, label, icon: Icon, tone }) => (
          <Card key={key} size="sm">
            <CardContent className="flex items-center justify-between gap-4 py-1">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
                <p className="mt-1 font-heading text-2xl font-semibold tabular-nums">{data.metrics[key]}</p>
              </div>
              <Icon size={24} weight="duotone" className={tone} aria-hidden="true" />
            </CardContent>
          </Card>
        ))}
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(20rem,0.8fr)]">
        <Card>
          <CardHeader className="border-b">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Network overview</CardTitle>
                <CardDescription>Active lanes from current shipment and inquiry records.</CardDescription>
              </div>
              <Badge variant="outline" className="gap-1.5"><MapPin size={13} /> Schematic route network</Badge>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            {/* ponytail: no coordinates or tile-provider keys, so this stays a truthful schematic; upgrade to MapLibre with an approved provider/geocoder when those inputs exist. */}
            <SchematicNetwork lanes={data.lanes} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Needs attention</CardTitle>
            <CardDescription>Risk, holds, and high-priority work sorted deterministically.</CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            {data.attention.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">No shipments need attention.</p>
            ) : (
              <ul className="divide-y divide-border" aria-label="Shipments needing attention">
                {data.attention.map(({ shipment, customer, inquiry, waitingMinutes }) => (
                  <li key={shipment.id}>
                    <Link to={`/shipments/${shipment.id}`} className="block rounded-lg px-2 py-3 outline-none transition-colors hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-medium">{shipment.job_number ?? `Shipment #${shipment.id}`}</p>
                          <p className="truncate text-xs text-muted-foreground">{customer?.name ?? "Unknown customer"}</p>
                        </div>
                        <span className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground"><Clock size={13} /> {formatWaiting(waitingMinutes)}</span>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        {inquiry && <span className="text-xs text-muted-foreground">{inquiry.origin} → {inquiry.destination}</span>}
                        <StageBadge stage={shipment.stage} />
                        {shipment.is_at_risk && <Badge variant="destructive">At risk</Badge>}
                        {shipment.is_on_hold && <Badge variant="outline">On hold</Badge>}
                        {shipment.priority === "high" && <Badge variant="secondary">High priority</Badge>}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Pipeline</CardTitle>
          <CardDescription>Shipment volume by macro phase, derived from the canonical stage metadata.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 pt-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {data.pipeline.map((phase) => (
            <div key={phase.key} className="space-y-2">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-sm font-medium">{phase.label}</span>
                <span className="font-heading text-lg font-semibold tabular-nums">{phase.count}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted" role="img" aria-label={`${phase.label}: ${phase.count} shipments`}>
                <div className="h-full rounded-full bg-accent-foreground" style={{ width: `${Math.min(100, phase.count ? Math.max(16, phase.count / Math.max(1, data.metrics.active) * 100) : 0)}%` }} />
              </div>
              <p className="text-xs text-muted-foreground">{phase.stages.map((stage) => labelFor(stage)).join(" · ")}</p>
            </div>
          ))}
          {data.pipeline.length === 0 && <p className="text-sm text-muted-foreground">Stage metadata is unavailable.</p>}
        </CardContent>
      </Card>

      <p className="flex items-center gap-2 text-xs text-muted-foreground"><UserCircle size={14} /> Metrics exclude cancelled and invoiced shipments from active operations.</p>
    </div>
  )
}
