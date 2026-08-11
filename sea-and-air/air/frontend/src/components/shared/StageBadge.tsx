import { CheckCircle, Circle } from "@phosphor-icons/react"
import { useStages } from "@/hooks/useStages"
import type { ShipmentStage } from "@/lib/api/types"
import { cn } from "@/lib/utils"

// Two-tone convention, consistent everywhere a stage appears: invoiced (the
// terminal stage) is the only "success" state; every other stage reads as
// "in progress" so a glance at the badge alone never has to be interpreted
// against tribal knowledge of the seventeen-stage order (that order lives
// in useStages/meta).
export function StageBadge({ stage, className }: { stage: ShipmentStage; className?: string }) {
  const { labelFor } = useStages()
  const isComplete = stage === "invoice_to_customer"

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        isComplete
          ? "bg-status-success/10 text-status-success"
          : "bg-status-info-bg text-status-info",
        className,
      )}
    >
      {isComplete ? <CheckCircle size={14} weight="fill" /> : <Circle size={14} weight="fill" />}
      {labelFor(stage)}
    </span>
  )
}
