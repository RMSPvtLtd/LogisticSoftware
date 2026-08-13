import { useEffect, useState } from "react"
import type { StageGroupCount } from "@/lib/dashboard"

// Custom CSS bar chart -- no charting library. Widths animate from 0 on
// mount via a plain CSS transition (GPU-friendly, no JS animation loop).
export function StageBreakdownBar({ data, total }: { data: StageGroupCount[]; total: number }) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(id)
  }, [])

  if (total === 0 || data.length === 0) return null

  return (
    <div className="space-y-3">
      {data.map(({ group, count }) => {
        const pct = Math.round((count / total) * 100)
        return (
          <div key={group} className="space-y-1">
            <div className="flex items-baseline justify-between text-xs">
              <span className="font-medium text-foreground">{group}</span>
              <span className="tabular-nums text-muted-foreground">
                {count} · {pct}%
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-[var(--motion-slow)] ease-[var(--motion-ease-out)]"
                style={{ width: mounted ? `${pct}%` : "0%" }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
