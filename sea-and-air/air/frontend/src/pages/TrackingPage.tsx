import { useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { MagnifyingGlass, Warning } from "@phosphor-icons/react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { StageChecklist } from "@/components/shared/StageChecklist"
import { EventTimeline } from "@/components/shared/EventTimeline"
import { LoadingState } from "@/components/shared/States"
import { useAsync } from "@/hooks/useAsync"
import { useStages } from "@/hooks/useStages"
import { trackingApi } from "@/lib/api/client"

const MODE_LABEL: Record<string, string> = { air: "Air Freight", sea: "Sea Freight", road: "Road Freight" }

export function TrackingPage() {
  const { reference } = useParams<{ reference?: string }>()
  const navigate = useNavigate()
  const [query, setQuery] = useState(reference ?? "")

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = query.trim()
    if (trimmed) navigate(`/track/${encodeURIComponent(trimmed)}`)
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="font-heading text-2xl font-semibold text-foreground sm:text-3xl">Track Your Shipment</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Enter your job number or any reference number (container, MAWB, HAWB, MBL, HBL).
        </p>
      </div>

      <form onSubmit={handleSearch} className="mx-auto flex max-w-md gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. RAZ-2026-00001"
          className="text-center tabular-nums sm:text-left"
          aria-label="Shipment reference number"
        />
        <Button type="submit" className="shrink-0 gap-1.5">
          <MagnifyingGlass size={16} />
          Track
        </Button>
      </form>

      {reference && <TrackingResultView reference={reference} />}
    </div>
  )
}

function TrackingResultView({ reference }: { reference: string }) {
  const { stages, labelFor } = useStages()
  const result = useAsync(() => trackingApi.track(reference), [reference])

  if (result.loading || stages.length === 0) return <LoadingState rows={4} />

  if (result.error) {
    return (
      <Card className="mx-auto max-w-md border-dashed">
        <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
          <Warning size={28} className="text-muted-foreground" />
          <p className="font-heading text-base font-medium text-foreground">We couldn't find that shipment</p>
          <p className="max-w-sm text-sm text-muted-foreground">
            {result.error.includes("multiple")
              ? "This reference matches more than one shipment. Please use your job number instead, or contact your account manager."
              : "Double-check the reference number and try again, or contact your Raaziq account manager for help."}
          </p>
        </CardContent>
      </Card>
    )
  }

  const r = result.data!

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div className="text-center">
        <p className="font-heading text-xl font-semibold tabular-nums text-foreground">
          {r.job_number ?? labelFor(r.stage)}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {r.origin} → {r.destination} · {MODE_LABEL[r.mode]}
        </p>
      </div>

      {r.at_risk && (
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
