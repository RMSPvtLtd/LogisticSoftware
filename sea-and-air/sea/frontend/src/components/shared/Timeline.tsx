import { CheckCircle } from "@phosphor-icons/react"
import { formatDateTime } from "@/lib/format"
import type { TrackingEvent } from "@/lib/api/types"
import { cn } from "@/lib/utils"

// Renders the tracking events the API returns, already sorted most-recent-
// first by the backend -- this component doesn't re-sort or interpret
// event types, it just displays whatever list it's given.
export function Timeline({ events }: { events: TrackingEvent[] }) {
  return (
    <ol className="flex flex-col">
      {events.map((event, i) => (
        <li key={`${event.type}-${event.timestamp}-${i}`} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span
              className={cn(
                "flex size-7 shrink-0 items-center justify-center rounded-full border-2",
                "border-status-success bg-status-success text-status-success-foreground",
              )}
              aria-hidden="true"
            >
              <CheckCircle size={16} weight="fill" />
            </span>
            {i !== events.length - 1 && (
              <span className="w-0.5 grow bg-status-success" aria-hidden="true" />
            )}
          </div>
          <div className={cn("pb-6", i === events.length - 1 && "pb-0")}>
            <p className="text-sm font-medium text-foreground">{event.type}</p>
            {event.timestamp && (
              <p className="text-xs text-muted-foreground tabular-nums">{formatDateTime(event.timestamp)}</p>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}
