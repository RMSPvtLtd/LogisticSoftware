import { useParams } from "react-router-dom"
import { Prohibit, Warning } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { StageChecklist } from "@/components/shared/StageChecklist"
import { EventTimeline } from "@/components/shared/EventTimeline"
import { LoadingState, ErrorState } from "@/components/shared/States"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { useAsync } from "@/hooks/useAsync"
import { useCustomerAuth } from "@/hooks/useCustomerAuth"
import { customerPortalApi } from "@/lib/api/client"

const MODE_LABEL: Record<string, string> = { air: "Air Freight", sea: "Sea Freight", road: "Road Freight" }

export function CustomerShipmentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { token } = useCustomerAuth()
  const shipmentId = Number(id)

  const result = useAsync(() => customerPortalApi.shipment(token!, shipmentId), [token, shipmentId])

  if (result.loading) return <LoadingState rows={4} />
  if (result.error || !result.data) {
    return <ErrorState message={result.error ?? "Shipment not found."} onRetry={result.reload} />
  }

  const r = result.data

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            {r.job_number ?? `Inquiry #${shipmentId}`}
            {r.is_cancelled && <Badge variant="secondary">Cancelled</Badge>}
          </span>
        }
        description={`${r.origin} → ${r.destination} · ${MODE_LABEL[r.mode]}`}
      />

      {r.is_cancelled && (
        <div className="flex items-start gap-2.5 rounded-xl bg-muted px-4 py-3 text-sm text-muted-foreground">
          <Prohibit size={18} weight="fill" className="mt-0.5 shrink-0" />
          <p>{r.cancellation_note ?? "This shipment has been cancelled."}</p>
        </div>
      )}

      {!r.is_cancelled && r.at_risk && (
        <div className="flex items-start gap-2.5 rounded-xl bg-status-warning-bg px-4 py-3 text-sm text-status-warning">
          <Warning size={18} weight="fill" className="mt-0.5 shrink-0" />
          <p>
            This shipment may be experiencing a delay. Contact your Raaziq account manager for the latest
            details.
          </p>
        </div>
      )}

      <Card>
        <CardContent className="py-6">
          <p className="mb-4 text-xs font-medium tracking-wide text-muted-foreground uppercase">Current Status</p>
          <StageChecklist items={r.checklist} />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="py-6">
          <p className="mb-4 text-xs font-medium tracking-wide text-muted-foreground uppercase">Activity</p>
          <EventTimeline entries={r.status_history} />
        </CardContent>
      </Card>

      {r.references.length > 0 && (
        <Card>
          <CardContent className="py-6">
            <p className="mb-3 text-xs font-medium tracking-wide text-muted-foreground uppercase">References</p>
            <ul className="space-y-1.5 text-sm">
              {r.references.map((ref, i) => (
                <li key={i} className="flex items-center justify-between rounded-lg bg-muted px-3 py-1.5">
                  <span className="text-muted-foreground">{ref.type.replace("_", " ")}</span>
                  <span className="font-medium tabular-nums">{ref.value}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
