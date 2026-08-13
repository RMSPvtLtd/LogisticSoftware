import type { ReactNode } from "react"
import { ArrowClockwise, WarningCircle } from "@phosphor-icons/react"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
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

// Skeleton matching a real table's shape (header row + N body rows of M
// cells) so there's no layout reflow once data arrives.
export function TableSkeleton({ columns = 5, rows = 6 }: { columns?: number; rows?: number }) {
  return (
    <div className="space-y-2" role="status" aria-label="Loading table">
      <div className="flex gap-4 border-b border-border pb-2">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-24 rounded" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 py-1.5">
          {Array.from({ length: columns }).map((_, c) => (
            <Skeleton key={c} className="h-4 w-24 rounded" />
          ))}
        </div>
      ))}
    </div>
  )
}

// Matches DashboardPage's real layout (5 KPI cards + stage chart + activity
// list) so the entrance stagger has something stable to animate into.
export function DashboardSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading dashboard">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i} className="gap-2">
            <div className="px-(--card-spacing)">
              <Skeleton className="h-3 w-20 rounded" />
              <Skeleton className="mt-2 h-7 w-12 rounded" />
            </div>
          </Card>
        ))}
      </div>
      <Card>
        <div className="space-y-3 px-(--card-spacing)">
          <Skeleton className="h-4 w-32 rounded" />
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-3 w-full rounded" />
          ))}
        </div>
      </Card>
      <Card>
        <div className="space-y-3 px-(--card-spacing)">
          <Skeleton className="h-4 w-28 rounded" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-full rounded" />
          ))}
        </div>
      </Card>
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
