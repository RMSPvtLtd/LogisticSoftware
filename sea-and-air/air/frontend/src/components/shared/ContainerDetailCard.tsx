import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import type { SeaContainerDetail } from "@/lib/api/types"

// Every field SAPT's per-voyage detail table exposes, grouped the way the
// source table groups them, with a fallback dash for anything the provider
// didn't have. Field values are provider-formatted strings (dates included)
// -- shown as-is, not reformatted, since they're supplementary detail
// rather than the primary timeline (which does get reformatted).
const FIELD_GROUPS: { title: string; fields: [string, keyof SeaContainerDetail][] }[] = [
  {
    title: "Voyage",
    fields: [
      ["Owner", "owner"],
      ["BL / Shipping Bill No.", "bl_number"],
      ["Container Size/Type", "container_size_type"],
      ["Vessel Voyage", "vessel_voyage"],
      ["VIR No.", "vir_number"],
    ],
  },
  {
    title: "Timing",
    fields: [
      ["ETA", "eta"],
      ["ETD", "etd"],
      ["Gate In", "gate_in_time"],
      ["Gate Out", "gate_out_time"],
      ["Discharge", "discharge_time"],
      ["Load", "load_time"],
      ["DO Issuance", "do_issuance_date"],
      ["DO Expiry", "do_expiry_date"],
    ],
  },
  {
    title: "Custody & Seals",
    fields: [
      ["Current Position", "current_position"],
      ["Custom Status", "custom_status"],
      ["Custom Seal No.", "custom_seal_number"],
      ["Line Seal No.", "line_seal_number"],
      ["Security Seal No.", "security_seal_number"],
      ["Other Seal No.", "other_seal_number"],
      ["Present Holds", "present_holds"],
    ],
  },
  {
    title: "Cargo",
    fields: [
      ["Commodity", "commodity"],
      ["Weight", "weight"],
      ["Weighment", "weighment"],
      ["Scanning", "scanning"],
    ],
  },
]

export function ContainerDetailCard({ detail }: { detail: SeaContainerDetail }) {
  return (
    <Card>
      <CardContent className="space-y-5 py-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {detail.category && <Badge variant="outline">{detail.category}</Badge>}
            {detail.status_code && <Badge variant="outline">{detail.status_code}</Badge>}
          </div>
          {(detail.origin || detail.destination) && (
            <p className="text-sm text-muted-foreground">
              {detail.origin ?? "—"} → {detail.destination ?? "—"}
            </p>
          )}
        </div>

        {FIELD_GROUPS.map((group) => {
          const visibleFields = group.fields.filter(([, key]) => detail[key])
          if (visibleFields.length === 0) return null
          return (
            <div key={group.title}>
              <p className="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                {group.title}
              </p>
              <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
                {visibleFields.map(([label, key]) => (
                  <div key={key} className="flex items-baseline justify-between gap-3 text-sm">
                    <dt className="text-muted-foreground">{label}</dt>
                    <dd className="text-right font-medium text-foreground">{detail[key]}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
