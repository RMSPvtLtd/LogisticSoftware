import { CheckCircle, Warning } from "@phosphor-icons/react"
import { cn } from "@/lib/utils"

export function RiskBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full bg-status-warning-bg px-2.5 py-1 text-xs font-medium text-status-warning",
        className,
      )}
    >
      <Warning size={14} weight="fill" />
      At Risk
    </span>
  )
}

export function NoRiskBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full bg-status-success/10 px-2.5 py-1 text-xs font-medium text-status-success",
        className,
      )}
    >
      <CheckCircle size={14} weight="fill" />
      No Risk
    </span>
  )
}
