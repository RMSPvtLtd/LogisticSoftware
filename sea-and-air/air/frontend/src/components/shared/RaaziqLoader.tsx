// Raaziq's signature loading indicator. The vehicle stays put in the center
// of the frame; a periodic field of route markers flows past underneath it
// (translated by exactly one dot-spacing and looped -- since the field is
// periodic at that spacing, the loop is seamless with zero JS). That's what
// reads as "the vehicle is moving forward" without it needing to travel and
// reset, which used to look like a jump-cut at the loop boundary. The marker
// conveyor always animates, including for "progress", so the loader never
// reads as frozen even when the vehicle itself is holding a real position.
// Three variants:
//   - "full": page/section-level loading moment, looping.
//   - "inline": compact version next to a button/panel while a mutation is
//     in flight, looping.
//   - "progress": position is driven by real data (a shipment's stage
//     index), not decoration -- vehicle eases to its real position.
// A fixed sky marker sits in the corner, independent of the vehicle's
// position: a crescent moon in light mode, a sun in dark mode (built with an
// SVG mask so the crescent cutout never depends on matching a background
// color).
// prefers-reduced-motion is handled globally in index.css; this component
// has no separate reduced-motion branch.

import { useId } from "react"
import { Airplane, Boat } from "@phosphor-icons/react"
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
  vehicle?: "truck" | "plane" | "ship"
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

// A gentle sine-wave line under the ship instead of road dots -- the wave
// is periodic at WAVE_PERIOD, so the same shift-and-loop trick used for the
// dots applies here too. Reads as "sea" regardless of how the vehicle icon
// itself is drawn.
const WAVE_PERIOD = 32
const waveSegment = `q ${WAVE_PERIOD / 4} -3 ${WAVE_PERIOD / 2} 0 q ${WAVE_PERIOD / 4} 3 ${WAVE_PERIOD / 2} 0 `
const waveRepeats = Math.ceil((ROUTE_WIDTH + WAVE_PERIOD * 2) / WAVE_PERIOD)
const WAVE_PATH = `M ${ROUTE_X_START - WAVE_PERIOD} ${DOT_Y} ` + waveSegment.repeat(waveRepeats)

export function RaaziqLoader({ variant, vehicle = "truck", progress = 0, label, className }: RaaziqLoaderProps) {
  const isInline = variant === "inline"
  const width = isInline ? 120 : 240
  const height = isInline ? 32 : 60
  const clampedProgress = Math.min(1, Math.max(0, progress))
  const truckX = variant === "progress" ? ROUTE_X_START + clampedProgress * ROUTE_WIDTH : TRUCK_CENTER_X
  const maskId = useId()
  const vehicleTransition = variant === "progress" ? "var(--motion-base) var(--motion-ease-out)" : undefined

  return (
    <div
      role="status"
      aria-label={label ?? "Loading"}
      className={cn("flex flex-col items-center gap-2", className)}
    >
      {/* Fixed pixel box (not scaled by the SVG's viewBox) so the plane/ship
          icon overlay stays crisp at the "inline" size instead of shrinking
          along with the vector artwork underneath it. */}
      <div className="relative text-primary" style={{ width, height }}>
        <svg viewBox="0 0 240 60" width={width} height={height} aria-hidden="true">
          {/* Route markers -- periodic, so shifting by exactly one period and
              looping is a seamless conveyor. Always animating so the loader
              never reads as frozen. Ship gets a sea-wave line instead of
              road dots, since that's the one cue that doesn't depend on the
              vehicle icon's own shape. */}
          {vehicle === "ship" ? (
            <g
              clipPath="inset(0 8px 0 8px)"
              style={{ animation: `wave-conveyor ${WAVE_PERIOD * 27.5}ms linear infinite` }}
            >
              <path d={WAVE_PATH} fill="none" stroke="currentColor" strokeOpacity="0.35" strokeWidth="1.5" />
            </g>
          ) : (
            <g
              clipPath="inset(0 8px 0 8px)"
              style={{ animation: `dot-conveyor ${DOT_SPACING * 55}ms linear infinite` }}
            >
              {DOT_XS.map((x) => (
                <circle key={x} cx={x} cy={DOT_Y} r="2" fill="currentColor" fillOpacity="0.3" />
              ))}
            </g>
          )}

          {/* Sky marker -- fixed in the corner, distant from the vehicle:
              crescent moon (light) swaps to a sun (dark), cut with a mask so
              the crescent never depends on matching a background color. */}
          <mask id={maskId}>
            <rect width="240" height="60" fill="black" />
            <circle cx="212" cy="12" r="5" fill="white" />
            <circle cx="215" cy="9" r="5" fill="black" />
          </mask>
          <g className="dark:hidden">
            <circle cx="212" cy="12" r="5" fill="currentColor" mask={`url(#${maskId})`} />
          </g>
          <g className="hidden dark:block text-status-warning">
            <circle cx="212" cy="12" r="4" fill="currentColor" />
            {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
              <line
                key={deg}
                x1="212"
                y1="5"
                x2="212"
                y2="2.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                transform={`rotate(${deg} 212 12)`}
              />
            ))}
          </g>

          {/* Truck -- hand-drawn vector, scales fine with the viewBox. */}
          {vehicle === "truck" && (
            <g
              style={{
                transform: `translateX(${truckX - TRUCK_CENTER_X}px)`,
                transition: vehicleTransition && `transform ${vehicleTransition}`,
              }}
            >
              <rect x="88" y="24" width="26" height="16" rx="2" fill="currentColor" />
              <path d="M114 28h9l6 6v6h-15z" fill="currentColor" />
              <rect x="120" y="30" width="6" height="5" rx="1" className="fill-background" />
              <circle cx="96" cy="42" r="3.5" fill="currentColor" />
              <circle cx="118" cy="42" r="3.5" fill="currentColor" />
            </g>
          )}
        </svg>

        {/* Plane/ship -- real Phosphor icons rendered as an HTML overlay at
            a fixed pixel size, not inside the SVG's viewBox, so they stay
            legible instead of shrinking to a blob at the "inline" scale. */}
        {vehicle !== "truck" && (
          <div
            className="absolute flex items-center justify-center"
            style={{
              left: `${(truckX / 240) * 100}%`,
              top: "58%",
              transform: "translate(-50%, -50%)",
              transition: vehicleTransition && `left ${vehicleTransition}`,
            }}
          >
            {vehicle === "plane" ? (
              <Airplane size={isInline ? 20 : 26} weight="regular" />
            ) : (
              <Boat size={isInline ? 20 : 26} weight="regular" />
            )}
          </div>
        )}
      </div>
      {label && <p className="text-xs text-muted-foreground">{label}</p>}
    </div>
  )
}
