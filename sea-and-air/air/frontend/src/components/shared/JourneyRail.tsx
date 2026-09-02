import { Check } from "@phosphor-icons/react"
import { journeyRail } from "@/lib/shipment-operations"
import { cn } from "@/lib/utils"
import type { ShipmentStage, StageMeta } from "@/lib/api/types"

export function JourneyRail({ stages, currentStage }: { stages: StageMeta[]; currentStage: ShipmentStage }) {
  const items = journeyRail(stages, currentStage)

  if (!items.length) return null

  return (
    <ol className="flex min-w-max items-start gap-0" aria-label="Condensed shipment journey">
      {items.map((item, index) => (
        <li key={item.label} className="flex items-start">
          <div className="flex w-20 flex-col items-center text-center sm:w-24">
            <span
              className={cn(
                "flex size-6 items-center justify-center rounded-full border text-xs",
                item.state === "completed" && "border-status-success bg-status-success text-status-success-foreground",
                item.state === "current" && "border-status-info bg-status-info-bg text-status-info",
                item.state === "upcoming" && "border-border bg-background text-muted-foreground",
              )}
              aria-hidden="true"
            >
              {item.state === "completed" ? <Check size={13} weight="bold" /> : <span className="size-1.5 rounded-full bg-current" />}
            </span>
            <span className={cn("mt-1 text-xs font-medium", item.state === "upcoming" && "text-muted-foreground")}>{item.label}</span>
            {item.state === "current" && <span className="mt-0.5 text-[11px] text-status-info">Current</span>}
          </div>
          {index < items.length - 1 && <span className={cn("mt-3 h-0.5 w-6 sm:w-10", item.state === "completed" ? "bg-status-success" : "bg-border")} aria-hidden="true" />}
        </li>
      ))}
    </ol>
  )
}
