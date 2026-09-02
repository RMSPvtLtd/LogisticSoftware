import { ArrowRight } from "@phosphor-icons/react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { TransportMode } from "@/lib/api/types"

const MODE_LABEL: Record<TransportMode, string> = { air: "Air", sea: "Sea", road: "Road" }

export function RouteOverview({ origin, destination, mode }: { origin: string; destination: string; mode: TransportMode }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Route overview</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-3 text-sm">
          <span className="min-w-0 flex-1 font-medium">{origin}</span>
          <ArrowRight size={18} className="shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="min-w-0 flex-1 text-right font-medium">{destination}</span>
        </div>
        <p className="mt-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">{MODE_LABEL[mode]} route</p>
      </CardContent>
    </Card>
  )
}
