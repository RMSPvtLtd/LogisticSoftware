import { ArrowDown, ArrowUp } from "@phosphor-icons/react"
import { cn } from "@/lib/utils"
import type { Priority } from "@/lib/api/types"

// Medium is the default for every shipment, so (like RiskBadge, which only
// renders when is_at_risk is true) nothing is shown for it -- a badge only
// appears when priority deviates from the baseline.
export function PriorityBadge({ priority, className }: { priority: Priority; className?: string }) {
  if (priority === "medium") return null

  const isHigh = priority === "high"

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        isHigh ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground",
        className,
      )}
    >
      {isHigh ? <ArrowUp size={14} weight="bold" /> : <ArrowDown size={14} weight="bold" />}
      {isHigh ? "High Priority" : "Low Priority"}
    </span>
  )
}
