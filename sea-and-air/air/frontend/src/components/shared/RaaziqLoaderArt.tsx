import { useId } from "react"

// Scene artwork for RaaziqLoader's air/sea variants.
//
// BoatScene is a direct recreation of the reference CSS animation (Carlos
// Gavina's "Boat"), traced from the source GIF frame-by-frame rather than
// eyeballed: every coordinate below is measured off the original 400x300
// artwork, and the bob is its real amplitude (4px) and period (2.16s). Only
// the palette is changed -- the reference's coral/navy/sky-blue is remapped
// onto Raaziq's own tokens.
//
// PlaneScene is the matching air version: line-art jet holding position
// while clouds drift back past it, which is what reads as forward motion.

// ---------------------------------------------------------------- boat ----

// Water is the bottom half of a circle centred (202,160.5) r=100, with a
// wavy top edge (crests y~161, troughs y~170, period 36) -- measured.
// The swell itself travels: in the reference it moves right at exactly
// 1px/frame, i.e. one 36px period every 720ms. To animate that without the
// circle moving too, the circle becomes a clip and an oversized wavy band
// slides inside it -- the band runs a full period past each edge so the
// shift-and-loop never reveals a seam.
const SEA_CLIP = "M102 160.5h200A100 100 0 0 1 102 160.5Z"
const WAVE_BAND = `M30 165.5 q9 -9 18 0 ${"t18 0 ".repeat(19)}V270 H30 Z`

// Red hull-bottom scallops showing above the waterline: bottom halves of
// 14x7 ellipses along the hull's bottom edge.
const SCALLOP_XS = [143, 177, 212, 247]

// Smoke puffs rise up-and-left out of each funnel, growing as they go. Each
// funnel runs the same three-puff cycle, offset so the two streams don't
// pulse in lockstep.
const PUFF_DELAYS = [0, -0.72, -1.44]
const FUNNELS = [
  { x: 173, delayShift: 0 },
  { x: 213, delayShift: -0.36 },
]

export function BoatScene({ width }: { width: number }) {
  const seaClipId = useId()
  return (
    <svg
      width={width}
      height={(width * 300) / 400}
      viewBox="0 0 400 300"
      aria-hidden="true"
      className="overflow-visible"
    >
      {/* whole vessel bobs on the swell -- 4px, 2.16s, straight from the
          reference's own timing */}
      <g style={{ animation: "boat-bob 2160ms ease-in-out infinite" }}>
        {/* smoke, behind the funnels */}
        {FUNNELS.map((f) =>
          PUFF_DELAYS.map((d) => (
            <circle
              key={`${f.x}-${d}`}
              cx={f.x - 6}
              cy={80}
              r={3}
              fill="currentColor"
              fillOpacity="0.18"
              style={{
                transformBox: "fill-box",
                transformOrigin: "center",
                animation: `boat-smoke 2160ms linear infinite`,
                animationDelay: `${d + f.delayShift}s`,
              }}
            />
          )),
        )}

        {/* funnels (accent) + navy caps */}
        <path d="M169.5 92h8l5.2 21h-8z" className="fill-status-info" />
        <path d="M209.5 92h8l4.5 21h-9z" className="fill-status-info" />
        <rect x="169" y="88" width="8.5" height="4" fill="currentColor" />
        <rect x="209" y="88" width="8.5" height="4" fill="currentColor" />

        {/* white deck house */}
        <path d="M142 113h114l7 18H134z" className="fill-background" />
        {/* portholes */}
        <circle cx="224.5" cy="121" r="5" className="fill-muted-foreground" />
        <circle cx="234.5" cy="121" r="5" className="fill-muted-foreground" />
        <circle cx="244.5" cy="121" r="5" className="fill-muted-foreground" />

        {/* hull */}
        <path d="M114 132h179l-22 29H128z" fill="currentColor" />
        {/* red scalloped hull bottom, peeking above the waterline */}
        {SCALLOP_XS.map((x) => (
          <path key={x} d={`M${x - 14} 161a14 7 0 0 0 28 0z`} className="fill-status-info" />
        ))}
      </g>

      {/* sea -- drawn last so it laps over the hull's bottom edge */}
      <clipPath id={seaClipId}>
        <path d={SEA_CLIP} />
      </clipPath>
      <g clipPath={`url(#${seaClipId})`}>
        <path
          d={WAVE_BAND}
          className="fill-status-info"
          fillOpacity="0.28"
          style={{ animation: "sea-waves 720ms linear infinite" }}
        />
      </g>
    </svg>
  )
}

// --------------------------------------------------------------- plane ----

const STROKE = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const

// Line-art jet in 3/4 view pointing right: long fuselage, far wing swept
// up-left, near wing swept down-left, small tail stabilisers at the rear.
function planeBody() {
  return (
    <>
      <path d="M170 132h118c11 0 20 3 20 7s-9 7-20 7H170c-6 0-10-3-10-7s4-7 10-7z" {...STROKE} />
      <path d="M243 132 206 100h15l47 32" {...STROKE} />
      <path d="M232 146l-39 41h18l51-41" {...STROKE} />
      <path d="M176 132 161 112h10l19 20" {...STROKE} />
      <path d="M176 146 161 166h10l19-20" {...STROKE} />
      <path d="M207 176 241 154" {...STROKE} />
      <path d="M286 139h14" {...STROKE} />
    </>
  )
}

const CLOUD_D = "M9 21a7 7 0 0 1 0-14 7.4 7.4 0 0 1 1.3.12A9 9 0 0 1 27 9.2a6 6 0 0 1 4 11.8Z"

// Staggered lanes/sizes/speeds so the clouds don't read as one repeating
// sprite -- fixed values, not random, so they don't reshuffle on re-render.
const CLOUDS = [
  { y: 40, scale: 1.5, duration: 6.5, delay: 0 },
  { y: 196, scale: 1.05, duration: 9, delay: -3.4 },
  { y: 96, scale: 0.8, duration: 11.5, delay: -1.6 },
]

export function PlaneScene({ width }: { width: number }) {
  const fadeId = useId()
  const dashMaskId = useId()
  return (
    <svg
      width={width}
      height={(width * 230) / 400}
      viewBox="0 0 400 230"
      aria-hidden="true"
      className="overflow-visible"
    >
      {/* clouds drift back past the jet -- the cue that reads as the plane
          moving forward, same job the road dots do for the truck */}
      {CLOUDS.map((c) => (
        <g
          key={c.y}
          style={{ animation: `cloud-drift-x ${c.duration}s linear infinite`, animationDelay: `${c.delay}s` }}
          opacity="0.4"
        >
          <g transform={`translate(0 ${c.y}) scale(${c.scale})`}>
            <path d={CLOUD_D} {...STROKE} strokeWidth={3.2} />
          </g>
        </g>
      ))}

      {/* speed dashes -- same two lanes as before, but now streaming
          backward past the jet. Built as a dash pattern with an animated
          dashoffset (one 84px period per cycle) so the loop is seamless,
          and masked with a soft gradient at both ends so streaks fade in
          and out rather than popping at the lane edges. */}
      <defs>
        <linearGradient id={fadeId} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#fff" stopOpacity="0" />
          <stop offset="30%" stopColor="#fff" stopOpacity="1" />
          <stop offset="72%" stopColor="#fff" stopOpacity="1" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <mask id={dashMaskId}>
          <rect x="88" y="92" width="120" height="106" fill={`url(#${fadeId})`} />
        </mask>
      </defs>
      <g mask={`url(#${dashMaskId})`} opacity="0.45">
        <line
          x1="60"
          y1="105"
          x2="215"
          y2="105"
          {...STROKE}
          strokeWidth={4}
          strokeDasharray="6 12 36 30"
          style={{ animation: "speed-dash 1400ms linear infinite" }}
        />
        <line
          x1="60"
          y1="186"
          x2="215"
          y2="186"
          {...STROKE}
          strokeWidth={4}
          strokeDasharray="34 9 5 36"
          style={{ animation: "speed-dash 1400ms linear infinite" }}
        />
      </g>

      {planeBody()}
    </svg>
  )
}
