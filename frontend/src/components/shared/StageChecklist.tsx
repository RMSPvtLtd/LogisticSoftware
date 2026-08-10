import { CheckCircle } from "@phosphor-icons/react"
import { useStages } from "@/hooks/useStages"
import type { TrackingChecklistItem } from "@/lib/api/types"
import { cn } from "@/lib/utils"

// Renders the ordered stage progression the tracking API returns --
// completed / current / upcoming -- as a vertical stepper. Never encodes
// stage order itself; that comes entirely from `items` (server-supplied)
// and labels come from useStages.
export function StageChecklist({ items }: { items: TrackingChecklistItem[] }) {
  return (
    <ol className="flex flex-col">
      {items.map((item, i) => (
        <ChecklistRow key={item.stage} item={item} isLast={i === items.length - 1} />
      ))}
    </ol>
  )
}

function ChecklistRow({ item, isLast }: { item: TrackingChecklistItem; isLast: boolean }) {
  const { labelFor } = useStages()
  const isCompleted = item.status === "completed"
  const isCurrent = item.status === "current"

  return (
    <li className="flex gap-3">
      <div className="flex flex-col items-center">
        <span
          className={cn(
            "flex size-7 shrink-0 items-center justify-center rounded-full border-2",
            isCompleted && "border-status-success bg-status-success text-status-success-foreground",
            isCurrent && "border-status-info bg-status-info-bg text-status-info",
            !isCompleted && !isCurrent && "border-border bg-background text-muted-foreground",
          )}
          aria-hidden="true"
        >
          {isCompleted ? (
            <CheckCircle size={16} weight="fill" />
          ) : (
            <span className={cn("size-2 rounded-full", isCurrent ? "bg-status-info" : "bg-border")} />
          )}
        </span>
        {!isLast && (
          <span className={cn("w-0.5 grow", isCompleted ? "bg-status-success" : "bg-border")} aria-hidden="true" />
        )}
      </div>
      <div className={cn("pb-6", isLast && "pb-0")}>
        <p
          className={cn(
            "text-sm font-medium",
            isCurrent ? "text-foreground" : isCompleted ? "text-foreground" : "text-muted-foreground",
          )}
        >
          {labelFor(item.stage)}
        </p>
        {isCurrent && <p className="text-xs text-status-info">Current status</p>}
      </div>
    </li>
  )
}
