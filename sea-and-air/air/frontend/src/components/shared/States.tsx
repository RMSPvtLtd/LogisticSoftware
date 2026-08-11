import type { ReactNode } from "react"
import { ArrowClockwise, WarningCircle } from "@phosphor-icons/react"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"

export function LoadingState({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3" role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-xl border border-destructive/20 bg-destructive/5 px-6 py-10 text-center"
    >
      <WarningCircle size={28} className="text-destructive" />
      <p className="max-w-sm text-sm text-foreground">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5">
          <ArrowClockwise size={16} />
          Try again
        </Button>
      )}
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border px-6 py-14 text-center">
      {icon && <div className="mb-1 text-muted-foreground">{icon}</div>}
      <p className="font-heading text-base font-medium text-foreground">{title}</p>
      {description && <p className="max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}
