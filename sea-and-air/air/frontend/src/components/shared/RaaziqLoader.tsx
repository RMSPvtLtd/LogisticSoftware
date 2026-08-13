// Raaziq's signature loading indicator. The truck stays put in the center
// of the frame; a periodic field of road markers flows past underneath it
// (translated by exactly one dot-spacing and looped -- since the field is
// periodic at that spacing, the loop is seamless with zero JS). That's what
// reads as "the truck is moving forward" without the truck itself needing
// to travel and reset, which used to look like a jump-cut at the loop
// boundary. Three variants:
//   - "full": page/section-level loading moment, looping.
//   - "inline": compact version next to a button/panel while a mutation is
//     in flight, looping.
//   - "progress": position is driven by real data (a shipment's stage
//     index), not decoration -- truck eases to its real position, road
//     markers are static (there's a real destination, not an open loop).
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

const ROUTE_X_START = 8
const ROUTE_X_END = 232
const ROUTE_WIDTH = ROUTE_X_END - ROUTE_X_START
const TRUCK_CENTER_X = 120
const DOT_SPACING = 16
const DOT_Y = 46

// A dot every DOT_SPACING px, padded a spacing-unit past each edge so the
// translateX(-DOT_SPACING) loop never reveals a gap.
const DOT_XS = Array.from(
  { length: Math.ceil((ROUTE_WIDTH + DOT_SPACING * 2) / DOT_SPACING) + 1 },
  (_, i) => ROUTE_X_START - DOT_SPACING + i * DOT_SPACING,
)

export function RaaziqLoader({ variant, progress = 0, label, className }: RaaziqLoaderProps) {
  const isLooping = variant === "full" || variant === "inline"
  const height = variant === "inline" ? 32 : 60
  const clampedProgress = Math.min(1, Math.max(0, progress))
  const truckX = variant === "progress" ? ROUTE_X_START + clampedProgress * ROUTE_WIDTH : TRUCK_CENTER_X

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
        {/* Road markers -- the field is periodic at DOT_SPACING, so shifting
            it by exactly one spacing and looping is a seamless conveyor. */}
        <g
          clipPath="inset(0 8px 0 8px)"
          style={isLooping ? { animation: `dot-conveyor ${DOT_SPACING * 55}ms linear infinite` } : undefined}
        >
          {DOT_XS.map((x) => (
            <circle key={x} cx={x} cy={DOT_Y} r="2" fill="currentColor" fillOpacity="0.3" />
          ))}
        </g>

        {/* Truck -- fixed at center while looping; eases to a real position
            for the progress variant. */}
        <g
          style={{
            transform: `translateX(${truckX - TRUCK_CENTER_X}px)`,
            transition: variant === "progress" ? "transform var(--motion-base) var(--motion-ease-out)" : undefined,
          }}
        >
          {/* trailer */}
          <rect x="88" y="24" width="26" height="16" rx="2" fill="currentColor" />
          {/* cab */}
          <path d="M114 28h9l6 6v6h-15z" fill="currentColor" />
          <rect x="120" y="30" width="6" height="5" rx="1" className="fill-background" />
          {/* wheels */}
          <circle cx="96" cy="42" r="3.5" fill="currentColor" />
          <circle cx="118" cy="42" r="3.5" fill="currentColor" />
          {/* static accent, top-right of the cab -- fixed marker, no pulse */}
          <circle cx="132" cy="17" r="2.5" fill="currentColor" />
        </g>
      </svg>
      {label && <p className="text-xs text-muted-foreground">{label}</p>}
    </div>
  )
}
