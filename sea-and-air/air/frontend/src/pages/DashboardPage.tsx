import { useMemo } from "react"
import { Link } from "react-router-dom"
import { Airplane, CheckCircle, Package, ShieldWarning, Warning } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { DashboardSkeleton, ErrorState, EmptyState } from "@/components/shared/States"
import { RaaziqLoader } from "@/components/shared/RaaziqLoader"
import { RiskBadge } from "@/components/shared/RiskBadge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StageBreakdownBar } from "@/components/dashboard/StageBreakdownBar"
import { useAsync } from "@/hooks/useAsync"
import { useStages } from "@/hooks/useStages"
import { shipmentsApi, quotesApi } from "@/lib/api/client"
import { formatMoney, formatRelativeTime } from "@/lib/format"
import {
  activeShipmentsCount,
  airlineGroupCount,
  atRiskShipments,
  customsClearedCount,
  customsPendingCount,
  expiringSoonQuotes,
  recentActivity,
  stageGroupBreakdown,
} from "@/lib/dashboard"

export function DashboardPage() {
  const { stages, indexOf, groupFor, labelFor } = useStages()
  const shipments = useAsync(() => shipmentsApi.list(), [])
  const quotes = useAsync(() => quotesApi.list(), [])

  const loading = shipments.loading || quotes.loading || stages.length === 0
  const error = shipments.error ?? quotes.error

  const orderedGroups = useMemo(() => {
    const seen = new Set<string>()
    const groups: string[] = []
    for (const s of stages) {
      if (s.group && !seen.has(s.group)) {
        seen.add(s.group)
        groups.push(s.group)
      }
    }
    return groups
  }, [stages])

  const kpis = useMemo(() => {
    if (!shipments.data || stages.length === 0) return null
    const lastIndex = stages.length - 1
    return {
      active: activeShipmentsCount(shipments.data, indexOf, lastIndex),
      customsPending: customsPendingCount(shipments.data),
      customsCleared: customsClearedCount(shipments.data, indexOf),
      atRisk: atRiskShipments(shipments.data).length,
      airline: airlineGroupCount(shipments.data, groupFor),
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shipments.data, stages])

  const breakdown = useMemo(
    () => (shipments.data ? stageGroupBreakdown(shipments.data, groupFor, orderedGroups) : []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [shipments.data, orderedGroups],
  )

  const activity = useMemo(
    () => (shipments.data ? recentActivity(shipments.data, labelFor) : []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [shipments.data],
  )

  const atRisk = shipments.data ? atRiskShipments(shipments.data) : []
  const expiringQuotes = quotes.data ? expiringSoonQuotes(quotes.data) : []

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Overview" description="Raaziq operations at a glance." />
        <RaaziqLoader variant="full" label="Loading dashboard…" className="py-4" />
        <DashboardSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Overview" description="Raaziq operations at a glance." />
        <ErrorState
          message={error}
          onRetry={() => {
            shipments.reload()
            quotes.reload()
          }}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="stagger-in">
        <PageHeader title="Overview" description="Raaziq operations at a glance." />
      </div>

      <div className="stagger-in grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <KpiCard label="Active Shipments" value={kpis?.active ?? 0} icon={<Package size={18} />} />
        <KpiCard label="Customs Pending" value={kpis?.customsPending ?? 0} icon={<Warning size={18} />} tone="warning" />
        <KpiCard label="Customs Cleared" value={kpis?.customsCleared ?? 0} icon={<CheckCircle size={18} />} tone="success" />
        <KpiCard label="At-Risk" value={kpis?.atRisk ?? 0} icon={<ShieldWarning size={18} />} tone="warning" />
        <KpiCard label="Airline (departure–arrival)" value={kpis?.airline ?? 0} icon={<Airplane size={18} />} />
      </div>

      <Card className="stagger-in">
        <CardHeader>
          <CardTitle>Shipments by stage group</CardTitle>
        </CardHeader>
        <CardContent>
          {breakdown.length > 0 ? (
            <StageBreakdownBar data={breakdown} total={shipments.data?.length ?? 0} />
          ) : (
            <p className="text-sm text-muted-foreground">No shipments yet.</p>
          )}
        </CardContent>
      </Card>

      <div className="stagger-in grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Needs attention</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {atRisk.length === 0 && expiringQuotes.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nothing needs attention right now.</p>
            ) : (
              <>
                {atRisk.map((s) => (
                  <Link
                    key={s.id}
                    to={`/shipments/${s.id}`}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border p-3 text-sm transition-colors duration-[var(--motion-fast)] hover:border-ring"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-foreground">{s.job_number ?? `Shipment #${s.id}`}</p>
                      {s.risk_reason && <p className="truncate text-xs text-muted-foreground">{s.risk_reason}</p>}
                    </div>
                    <RiskBadge className="shrink-0" />
                  </Link>
                ))}
                {expiringQuotes.map((q) => (
                  <Link
                    key={q.id}
                    to={`/quotes/${q.id}`}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border p-3 text-sm transition-colors duration-[var(--motion-fast)] hover:border-ring"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-foreground">Quote #{q.id}</p>
                      <p className="text-xs text-muted-foreground">{formatMoney(q.total, q.currency)}</p>
                    </div>
                    <span className="shrink-0 text-xs text-status-warning">Expires soon</span>
                  </Link>
                ))}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
          </CardHeader>
          <CardContent>
            {activity.length === 0 ? (
              <EmptyState icon={<Package size={28} />} title="No activity yet" />
            ) : (
              <ul className="space-y-2.5">
                {activity.map(({ shipment, text }) => (
                  <li key={shipment.id}>
                    <Link
                      to={`/shipments/${shipment.id}`}
                      className="flex items-baseline justify-between gap-3 text-sm transition-colors duration-[var(--motion-fast)] hover:text-foreground"
                    >
                      <span className="min-w-0 truncate text-foreground">{text}</span>
                      <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                        {formatRelativeTime(shipment.updated_at)}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function KpiCard({
  label,
  value,
  icon,
  tone,
}: {
  label: string
  value: number
  icon: React.ReactNode
  tone?: "warning" | "success"
}) {
  return (
    <Card size="sm">
      <CardContent className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="mt-1 font-heading text-2xl font-semibold tabular-nums text-foreground">{value}</p>
        </div>
        <span
          className={
            tone === "warning"
              ? "text-status-warning"
              : tone === "success"
                ? "text-status-success"
                : "text-muted-foreground"
          }
        >
          {icon}
        </span>
      </CardContent>
    </Card>
  )
}
