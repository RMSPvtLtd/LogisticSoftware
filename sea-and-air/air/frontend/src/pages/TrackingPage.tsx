import { useEffect, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { MagnifyingGlass, Prohibit, Warning } from "@phosphor-icons/react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { StageChecklist } from "@/components/shared/StageChecklist"
import { EventTimeline } from "@/components/shared/EventTimeline"
import { JourneyRail } from "@/components/shared/JourneyRail"
import { RouteOverview } from "@/components/shared/RouteOverview"
import { ContainerTimeline } from "@/components/shared/ContainerTimeline"
import { ContainerDetailCard } from "@/components/shared/ContainerDetailCard"
import { LoadingState } from "@/components/shared/States"
import { useAsync } from "@/hooks/useAsync"
import { useStages } from "@/hooks/useStages"
import { trackingApi, seaTrackingApi, ApiError } from "@/lib/api/client"
import { formatRelativeTime } from "@/lib/format"
import { customerJourneyState } from "@/lib/shipment-operations"
import type { SeaTrackingResult } from "@/lib/api/types"

const MODE_LABEL: Record<string, string> = { air: "Air Freight", sea: "Sea Freight", road: "Road Freight" }

type TrackerMode = "air" | "sea"

export function TrackingPage() {
  const { reference, containerNumber } = useParams<{ reference?: string; containerNumber?: string }>()
  const location = useLocation()
  const navigate = useNavigate()

  const mode: TrackerMode = location.pathname.startsWith("/track/sea") ? "sea" : "air"
  const activeValue = mode === "sea" ? containerNumber : reference

  const [query, setQuery] = useState(activeValue ?? "")

  function handleModeChange(next: string) {
    setQuery("")
    navigate(next === "sea" ? "/track/sea" : "/track")
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return
    navigate(mode === "sea" ? `/track/sea/${encodeURIComponent(trimmed)}` : `/track/${encodeURIComponent(trimmed)}`)
  }

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-border bg-card px-4 py-8 sm:px-8">
      <div className="text-center">
        <h1 className="font-heading text-2xl font-semibold text-foreground sm:text-3xl">Track Your Shipment</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {mode === "sea"
            ? "Enter your container number to see its current status."
            : "Enter your job number or any reference number (container, MAWB, HAWB, MBL, HBL)."}
        </p>
      </div>

      <div className="flex flex-col items-center gap-4">
        <Tabs value={mode} onValueChange={handleModeChange}>
          <TabsList>
            <TabsTrigger value="air">Air</TabsTrigger>
            <TabsTrigger value="sea">Sea</TabsTrigger>
          </TabsList>
        </Tabs>

        <form onSubmit={handleSearch} className="flex w-full max-w-md gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={mode === "sea" ? "e.g. TESU1234565" : "e.g. RAZ-2026-00001"}
            className="text-center tabular-nums uppercase sm:text-left"
            aria-label={mode === "sea" ? "Container number" : "Shipment reference number"}
          />
          <Button type="submit" className="shrink-0 gap-1.5">
            <MagnifyingGlass size={16} />
            Track
          </Button>
        </form>
      </div>
      </section>

      {mode === "air" && reference && <AirTrackingResultView reference={reference} />}
      {mode === "sea" && containerNumber && <SeaTrackingResultView containerNumber={containerNumber} />}
    </div>
  )
}

function AirTrackingResultView({ reference }: { reference: string }) {
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
  const latest = r.status_history.toSorted((a, b) => b.timestamp.localeCompare(a.timestamp))[0]
  const journey = customerJourneyState(r.checklist, r.is_cancelled)

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="text-center">
        <p className="font-heading text-xl font-semibold tabular-nums text-foreground">
          {r.job_number ?? labelFor(r.stage)}
          {r.is_cancelled && <span className="ml-2 align-middle text-sm font-normal text-muted-foreground">(Cancelled)</span>}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {r.origin} → {r.destination} · {MODE_LABEL[r.mode]}
        </p>
      </div>

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

      <div className="grid gap-4 md:grid-cols-2">
        <Card><CardContent className="py-5"><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{r.is_cancelled ? "Shipment status" : "Current milestone"}</p><p className="mt-2 font-heading text-xl font-semibold">{r.is_cancelled ? "Cancelled" : labelFor(r.stage)}</p><p className="mt-1 text-sm text-muted-foreground">{latest ? `Updated ${formatRelativeTime(latest.timestamp)}` : "No activity update yet"}</p><div className="mt-4 border-t border-border pt-3"><p className="text-xs text-muted-foreground">{r.is_cancelled ? "Last recorded milestone" : "Next milestone"}</p><p className="mt-1 text-sm font-medium">{r.is_cancelled ? labelFor(r.stage) : journey.next ? labelFor(journey.next.stage) : "Journey complete"}</p></div></CardContent></Card>
        <RouteOverview origin={r.origin} destination={r.destination} mode={r.mode} />
      </div>

      {!r.is_cancelled && <Card><CardContent className="overflow-x-auto py-5"><p className="mb-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Shipment journey</p><JourneyRail stages={stages} currentStage={r.stage} /></CardContent></Card>}

      <Card>
        <CardContent className="py-6">
          <p className="mb-4 text-xs font-medium tracking-wide text-muted-foreground uppercase">Current Status</p>
          <StageChecklist items={journey.items} />
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

// Maps HTTP status -> customer-facing copy, rather than trusting the
// backend's `detail` text for every case: the 404 message in particular
// names SAPT internally (useful in logs, never meant for a customer -- see
// Phase 8/10 of the SAPT integration plan: SAPT must never be named to the
// user). `useAsync` collapses errors to a string and loses the status code
// that distinction depends on, so this view manages its own fetch state.
function seaErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 422) return "Please enter a valid container number."
    if (err.status === 404) return "No tracking information was found for this container."
    if (err.status === 503) return "Tracking information is temporarily unavailable.\nPlease try again later."
  }
  return "We couldn't retrieve tracking information right now."
}

function SeaTrackingResultView({ containerNumber }: { containerNumber: string }) {
  const [state, setState] = useState<
    { status: "loading" } | { status: "error"; message: string } | { status: "success"; data: SeaTrackingResult }
  >({ status: "loading" })

  useEffect(() => {
    let cancelled = false
    setState({ status: "loading" })
    seaTrackingApi
      .track(containerNumber)
      .then((data) => {
        if (!cancelled) setState({ status: "success", data })
      })
      .catch((err) => {
        if (!cancelled) setState({ status: "error", message: seaErrorMessage(err) })
      })
    return () => {
      cancelled = true
    }
  }, [containerNumber])

  if (state.status === "loading") {
    return (
      <div className="mx-auto max-w-xl">
        <p className="mb-4 text-center text-sm text-muted-foreground">Fetching shipment information...</p>
        <LoadingState rows={3} />
      </div>
    )
  }

  if (state.status === "error") {
    return (
      <Card className="mx-auto max-w-md border-dashed">
        <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
          <Warning size={28} className="text-muted-foreground" />
          <p className="max-w-sm whitespace-pre-line text-sm text-foreground">{state.message}</p>
        </CardContent>
      </Card>
    )
  }

  const r = state.data
  const detail = r.details.find((item) => item.current_position || item.origin || item.destination)

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="text-center">
        <p className="font-heading text-xl font-semibold tabular-nums text-foreground">{r.container_number}</p>
        <p className="mt-1 text-sm text-muted-foreground">Terminal: {r.terminal}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2"><Card><CardContent className="py-5"><p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Current status</p><p className="mt-2 font-heading text-xl font-semibold text-foreground">{r.status}</p>{detail?.current_position && <><p className="mt-4 text-xs text-muted-foreground">Reported position</p><p className="mt-1 text-sm font-medium">{detail.current_position}</p></>}</CardContent></Card>{detail?.origin && detail.destination && <RouteOverview origin={detail.origin} destination={detail.destination} mode="sea" />}</div>

      <Card>
        <CardContent className="py-6">
          <p className="mb-4 text-xs font-medium tracking-wide text-muted-foreground uppercase">Timeline</p>
          {r.events.length > 0 ? (
            <ContainerTimeline events={r.events} />
          ) : (
            <p className="text-sm text-muted-foreground">No movement events recorded yet.</p>
          )}
        </CardContent>
      </Card>

      {r.details.length > 0 && (
        <div className="space-y-4">
          <p className="text-center text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Voyage Details
          </p>
          {r.details.map((detail, i) => (
            <ContainerDetailCard key={`${detail.bl_number ?? "voyage"}-${i}`} detail={detail} />
          ))}
        </div>
      )}
    </div>
  )
}
