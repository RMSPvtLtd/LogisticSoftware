import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { ArrowClockwise, CheckCircle, ClipboardText } from "@phosphor-icons/react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/components/shared/PageHeader"
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/States"
import { useAsync } from "@/hooks/useAsync"
import { useWorkerAuth } from "@/hooks/useWorkerAuth"
import { ApiError, workerPortalApi } from "@/lib/api/client"
import { formatRelativeTime } from "@/lib/format"
import type { WorkerQueueItem } from "@/lib/api/types"

// Chrome (identity, sign-out, sidebar) now lives in AppShell -- this page
// only owns the queue itself.
export function WorkerQueuePage() {
  const { worker, token, logout } = useWorkerAuth()
  const navigate = useNavigate()

  const queue = useAsync(() => workerPortalApi.queue(token!), [token])

  if (!worker || !token) return null // route guard already redirects; guards a render-before-redirect flash

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <PageHeader
        title={`Waiting for ${worker.area.name}`}
        action={
          <Button variant="ghost" size="icon" aria-label="Refresh" onClick={queue.reload}>
            <ArrowClockwise size={18} />
          </Button>
        }
      />

      {queue.loading && <LoadingState rows={3} />}

      {!queue.loading && queue.error && (
        <ErrorState
          message={queue.error}
          onRetry={() => {
            if (queue.error?.toLowerCase().includes("session")) {
              logout()
              navigate("/worker/login")
            } else {
              queue.reload()
            }
          }}
        />
      )}

      {!queue.loading && !queue.error && (queue.data?.length ?? 0) === 0 && (
        <EmptyState
          icon={<ClipboardText size={32} />}
          title="Nothing waiting right now"
          description={`Shipments will show up here as soon as they're ready for ${worker.area.name}.`}
        />
      )}

      {!queue.loading && !queue.error && (queue.data?.length ?? 0) > 0 && (
        <div className="space-y-3">
          {queue.data!.map((item) => (
            <QueueItemCard key={item.id} item={item} token={token} onCompleted={queue.reload} />
          ))}
        </div>
      )}
    </div>
  )
}

function QueueItemCard({
  item,
  token,
  onCompleted,
}: {
  item: WorkerQueueItem
  token: string
  onCompleted: () => void
}) {
  const [note, setNote] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function handleComplete() {
    setSubmitting(true)
    try {
      await workerPortalApi.complete(token, item.id, note.trim() || undefined)
      toast.success(`${item.job_number} marked done`)
      onCompleted()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not mark this shipment done.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card id={`queue-item-${item.id}`}>
      <CardContent className="space-y-3 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-heading text-base font-semibold tabular-nums text-foreground">{item.job_number}</p>
            <p className="text-sm text-muted-foreground">
              {item.customer_name} · {item.origin} → {item.destination}
            </p>
            <p className="text-sm text-muted-foreground">{item.cargo_type}</p>
          </div>
          <span className="shrink-0 text-xs text-muted-foreground">Waiting {formatRelativeTime(item.waiting_since)}</span>
        </div>

        {item.last_note && (
          <p className="rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">"{item.last_note}"</p>
        )}

        <Textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Note (optional)"
          rows={2}
          aria-label={`Note for ${item.job_number}`}
        />

        <Button onClick={handleComplete} disabled={submitting} className="w-full gap-1.5" size="lg">
          <CheckCircle size={18} weight="fill" />
          {submitting ? "Marking done…" : "Mark Done"}
        </Button>
      </CardContent>
    </Card>
  )
}
