import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { MagnifyingGlass, Warning } from "@phosphor-icons/react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { LoadingState } from "@/components/shared/States"
import { Timeline } from "@/components/shared/Timeline"
import { ContainerDetailCard } from "@/components/shared/ContainerDetailCard"
import { trackingApi, ApiError } from "@/lib/api/client"
import type { TrackingResult } from "@/lib/api/types"

// Maps HTTP status -> the exact user-facing copy from Phase 8 of the SAPT
// integration plan. Deliberately hardcoded here rather than trusting the
// backend's `detail` text for every case: the 404/503 backend messages are
// written for logs, not customers, and status-code mapping means the
// frontend's copy doesn't silently change if the backend's wording does.
function errorMessageFor(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 422) return "Please enter a valid container number."
    if (err.status === 404) return "No tracking information was found for this container."
    if (err.status === 503) return "Tracking information is temporarily unavailable.\nPlease try again later."
  }
  return "We couldn't retrieve tracking information right now."
}

type Status = "idle" | "loading" | "success" | "error"

export function SeaTrackerPage() {
  const { containerNumber: routeContainerNumber } = useParams<{ containerNumber?: string }>()
  const navigate = useNavigate()

  const [query, setQuery] = useState(routeContainerNumber ?? "")
  const [status, setStatus] = useState<Status>("idle")
  const [result, setResult] = useState<TrackingResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function runTrack(containerNumber: string) {
    setStatus("loading")
    setError(null)
    try {
      const data = await trackingApi.track(containerNumber)
      setResult(data)
      setStatus("success")
    } catch (err) {
      setError(errorMessageFor(err))
      setResult(null)
      setStatus("error")
    }
  }

  useEffect(() => {
    if (routeContainerNumber) {
      void runTrack(routeContainerNumber)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeContainerNumber])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return
    navigate(`/track/${encodeURIComponent(trimmed)}`)
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="font-heading text-2xl font-semibold text-foreground sm:text-3xl">Track Your Shipment</h1>
        <p className="mt-1 text-sm text-muted-foreground">Enter your container number to see its current status.</p>
      </div>

      <form onSubmit={handleSubmit} className="mx-auto flex max-w-md gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. CAAU2314798"
          className="text-center tabular-nums uppercase sm:text-left"
          aria-label="Container number"
        />
        <Button type="submit" className="shrink-0 gap-1.5" disabled={status === "loading"}>
          <MagnifyingGlass size={16} />
          Track
        </Button>
      </form>

      {status === "loading" && (
        <div className="mx-auto max-w-xl">
          <p className="mb-4 text-center text-sm text-muted-foreground">Fetching shipment information...</p>
          <LoadingState rows={3} />
        </div>
      )}

      {status === "error" && error && (
        <Card className="mx-auto max-w-md border-dashed">
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
            <Warning size={28} className="text-muted-foreground" />
            <p className="max-w-sm whitespace-pre-line text-sm text-foreground">{error}</p>
          </CardContent>
        </Card>
      )}

      {status === "success" && result && <TrackingResultView result={result} />}
    </div>
  )
}

function TrackingResultView({ result }: { result: TrackingResult }) {
  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div className="text-center">
        <p className="font-heading text-xl font-semibold tabular-nums text-foreground">{result.container_number}</p>
        <p className="mt-1 text-sm text-muted-foreground">Terminal: {result.terminal}</p>
      </div>

      <Card>
        <CardContent className="flex items-center justify-between py-5">
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Status</p>
          <p className="font-heading text-base font-semibold text-foreground">{result.status}</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="py-6">
          <p className="mb-4 text-xs font-medium tracking-wide text-muted-foreground uppercase">Timeline</p>
          {result.events.length > 0 ? (
            <Timeline events={result.events} />
          ) : (
            <p className="text-sm text-muted-foreground">No movement events recorded yet.</p>
          )}
        </CardContent>
      </Card>

      {result.details.length > 0 && (
        <div className="space-y-4">
          <p className="text-center text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Voyage Details
          </p>
          {result.details.map((detail, i) => (
            <ContainerDetailCard key={`${detail.bl_number ?? "voyage"}-${i}`} detail={detail} />
          ))}
        </div>
      )}
    </div>
  )
}
