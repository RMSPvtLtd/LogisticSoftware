// Raaziq's signature loading indicator -- a truck traveling a route line.
// Pure inline SVG (no raster asset), colored via currentColor so it follows
// the surrounding text color and theme automatically. Three variants:
//   - "full": page/section-level loading moment, looping.
//   - "inline": compact version next to a button/panel while a mutation is
//     in flight, looping.
//   - "progress": position is driven by real data (a shipment's stage
//     index), not decoration -- no loop, eases to its target position.
// prefers-reduced-motion is handled globally in index.css; this component
// has no separate reduced-motion branch.

import { cn } from "@/lib/utils"
import { useStages } from "@/hooks/useStages"
import type { ShipmentStage } from "@/lib/api/types"

export function useShipmentProgress(stage: ShipmentStage): number {
  const { stages, indexOf } = useStages()
  if (stages.length < 2) return 0
  const idx = indexOf(stage)
  if (idx < 0) return 0
  return idx / (stages.length - 1)
}

interface RaaziqLoaderProps {
  variant: "full" | "inline" | "progress"
  progress?: number // 0-1, used only for variant="progress"
  label?: string
  className?: string
}

const ROUTE_WIDTH = 200 // truck travel distance within the 240-wide viewBox

export function RaaziqLoader({ variant, progress = 0, label, className }: RaaziqLoaderProps) {
  const isLooping = variant === "full" || variant === "inline"
  const height = variant === "inline" ? 32 : 60
  const clampedProgress = Math.min(1, Math.max(0, progress))

  return (
    <div
      role="status"
      aria-label={label ?? "Loading"}
      className={cn("flex flex-col items-center gap-2", className)}
    >
      <svg
        viewBox="0 0 240 60"
        width={variant === "inline" ? 120 : 240}
        height={height}
        className="text-primary"
        aria-hidden="true"
      >
        {/* Route line */}
        <line
          x1="8"
          y1="46"
          x2="232"
          y2="46"
          stroke="currentColor"
          strokeOpacity="0.25"
          strokeWidth="2"
          strokeDasharray="6 6"
          style={isLooping ? { animation: "dash-flow 900ms linear infinite" } : undefined}
        />

        {/* Truck, positioned via a translating group */}
        <g
          style={
            isLooping
              ? { animation: "truck-drive 1.8s linear infinite", transformBox: "view-box" }
              : {
                  transform: `translateX(${clampedProgress * ROUTE_WIDTH}px)`,
                  transition: "transform var(--motion-base) var(--motion-ease-out)",
                }
          }
        >
          {/* trailer */}
          <rect x="8" y="24" width="26" height="16" rx="2" fill="currentColor" />
          {/* cab */}
          <path d="M34 28h9l6 6v6h-15z" fill="currentColor" />
          <rect x="40" y="30" width="6" height="5" rx="1" className="fill-background" />
          {/* wheels */}
          <circle cx="16" cy="42" r="3.5" fill="currentColor" />
          <circle cx="38" cy="42" r="3.5" fill="currentColor" />
          {/* current-position pulse, only meaningful for the progress variant */}
          {variant === "progress" && (
            <circle cx="45" cy="20" r="3" fill="currentColor" style={{ animation: "pulse-dot 1.6s ease-in-out infinite" }} />
          )}
        </g>
      </svg>
      {label && <p className="text-xs text-muted-foreground">{label}</p>}
    </div>
  )
}
