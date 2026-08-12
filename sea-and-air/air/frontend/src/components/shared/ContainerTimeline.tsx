import { CheckCircle } from "@phosphor-icons/react"
import { formatDateTime } from "@/lib/format"
import type { SeaTrackingEvent } from "@/lib/api/types"
import { cn } from "@/lib/utils"

// The sea vertical's container-tracking timeline -- named distinctly from
// EventTimeline (air's own stage-history component) since the two render
// different shapes (SeaTrackingEvent vs air's TrackingEvent) from two
// different backends. Events arrive already sorted most-recent-first.
export function ContainerTimeline({ events }: { events: SeaTrackingEvent[] }) {
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
