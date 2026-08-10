import { ArrowsClockwise, Robot, User, Wrench } from "@phosphor-icons/react"
import { useStages } from "@/hooks/useStages"
import { formatDateTime } from "@/lib/format"
import type { EventSource, ShipmentStage } from "@/lib/api/types"
import { cn } from "@/lib/utils"

export interface TimelineEntry {
  stage: ShipmentStage
  timestamp: string
  note: string | null
  actor?: string
  source?: EventSource
}

const SOURCE_ICON: Record<EventSource, typeof User> = {
  manual: User,
  automated: Robot,
  system: ArrowsClockwise,
  correction: Wrench,
}

const SOURCE_LABEL: Record<EventSource, string> = {
  manual: "Manual update",
  automated: "Automated update",
  system: "System",
  correction: "Correction",
}

// Most-recent-first reverse-chronological activity feed. Works for both the
// full ops StatusEvent list (actor/source present) and the reduced public
// tracking event list (neither present) -- the fields simply don't render
// when absent.
export function EventTimeline({ entries }: { entries: TimelineEntry[] }) {
  const { labelFor } = useStages()
  const ordered = [...entries].reverse()

  if (ordered.length === 0) {
    return <p className="text-sm text-muted-foreground">No activity recorded yet.</p>
  }

  return (
    <ol className="flex flex-col">
      {ordered.map((entry, i) => {
        const Icon = entry.source ? SOURCE_ICON[entry.source] : null
        const isLast = i === ordered.length - 1
        return (
          <li key={`${entry.timestamp}-${i}`} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full border border-border bg-muted text-muted-foreground">
                {Icon ? <Icon size={14} /> : <span className="size-1.5 rounded-full bg-current" />}
              </span>
              {!isLast && <span className="w-0.5 grow bg-border" aria-hidden="true" />}
            </div>
            <div className={cn("pb-5", isLast && "pb-0")}>
              <div className="flex flex-wrap items-baseline gap-x-2">
                <p className="text-sm font-medium text-foreground">{labelFor(entry.stage)}</p>
                <p className="text-xs text-muted-foreground tabular-nums">{formatDateTime(entry.timestamp)}</p>
                {entry.source && (
                  <span
                    className={cn(
                      "rounded px-1.5 py-0.5 text-[11px] font-medium",
                      entry.source === "correction" ? "bg-status-warning-bg text-status-warning" : "bg-muted text-muted-foreground",
                    )}
                  >
                    {SOURCE_LABEL[entry.source]}
                  </span>
                )}
              </div>
              {entry.note && <p className="mt-0.5 text-sm text-muted-foreground">{entry.note}</p>}
              {entry.actor && <p className="mt-0.5 text-xs text-muted-foreground">by {entry.actor}</p>}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
