import { useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"
import { ArrowLeft, CheckCircle, PauseCircle, PencilSimple, Prohibit, Trash, UsersThree, Warning } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { StageBadge } from "@/components/shared/StageBadge"
import { RiskBadge } from "@/components/shared/RiskBadge"
import { PriorityBadge } from "@/components/shared/PriorityBadge"
import { DocumentsCard } from "@/components/shared/DocumentsCard"
import { EventTimeline } from "@/components/shared/EventTimeline"
import { LoadingState, ErrorState } from "@/components/shared/States"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { useAsync } from "@/hooks/useAsync"
import { useStages } from "@/hooks/useStages"
import { areasApi, customersApi, inquiriesApi, shipmentsApi } from "@/lib/api/client"
import { ApiError } from "@/lib/api/client"
import { formatDate } from "@/lib/format"
import type { Priority, ReferenceType, ShipmentStage } from "@/lib/api/types"

const MODE_LABEL: Record<string, string> = { air: "Air", sea: "Sea", road: "Road" }
const REFERENCE_TYPES: ReferenceType[] = ["MAWB", "HAWB", "MBL", "HBL", "CONTAINER", "FORM_E", "LC", "PARTY_REFERENCE"]

export function ShipmentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const shipmentId = Number(id)
  const navigate = useNavigate()
  const { stages } = useStages()

  const shipment = useAsync(() => shipmentsApi.get(shipmentId), [shipmentId])
  const customer = useAsync(
    () => (shipment.data ? customersApi.get(shipment.data.customer_id) : Promise.resolve(null)),
    [shipment.data?.customer_id],
  )
  const inquiry = useAsync(
    () => (shipment.data ? inquiriesApi.get(shipment.data.inquiry_id) : Promise.resolve(null)),
    [shipment.data?.inquiry_id],
  )

  if (shipment.loading) return <LoadingState rows={6} />
  if (shipment.error || !shipment.data) {
    return <ErrorState message={shipment.error ?? "Shipment not found."} onRetry={shipment.reload} />
  }

  const s = shipment.data
  const currentIndex = stages.findIndex((st) => st.stage === s.stage)
  const nextStage = currentIndex >= 0 && currentIndex + 1 < stages.length ? stages[currentIndex + 1] : null

  return (
    <div>
      <Button variant="ghost" size="sm" className="mb-3 -ml-2 gap-1.5 text-muted-foreground" onClick={() => navigate("/shipments")}>
        <ArrowLeft size={16} />
        All shipments
      </Button>

      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            {s.job_number ?? `Inquiry #${s.inquiry_id}`}
            <StageBadge stage={s.stage} />
            {s.is_cancelled && <Badge variant="secondary">Cancelled</Badge>}
            {s.is_on_hold && <Badge className="bg-status-warning-bg text-status-warning">On Hold</Badge>}
            {!s.is_cancelled && s.is_at_risk && <RiskBadge />}
            <PriorityBadge priority={s.priority} />
          </span>
        }
        description={
          customer.data && inquiry.data
            ? `${customer.data.name} · ${inquiry.data.origin} → ${inquiry.data.destination} · ${MODE_LABEL[inquiry.data.mode]}`
            : undefined
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Status history</CardTitle>
            </CardHeader>
            <CardContent>
              <EventTimeline entries={s.status_events} />
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-col gap-6">
          {s.is_cancelled ? (
            <Card className="border-muted-foreground/20 bg-muted/40">
              <CardContent className="flex items-start gap-2.5 py-4 text-sm text-muted-foreground">
                <Prohibit size={18} weight="fill" className="mt-0.5 shrink-0" />
                <span>
                  Cancelled by {s.cancelled_by ?? "ops"} on {s.cancelled_at ? formatDate(s.cancelled_at) : "—"}.
                  {s.cancelled_reason && <> Reason: {s.cancelled_reason}</>}
                </span>
              </CardContent>
            </Card>
          ) : (
            <>
              <NextStageCard shipmentId={s.id} nextStage={nextStage} onDone={shipment.reload} />
              <CorrectionCard shipmentId={s.id} currentStage={s.stage} onDone={shipment.reload} />
            </>
          )}
          <HoldCard shipmentId={s.id} isOnHold={s.is_on_hold} holdReason={s.hold_reason} onDone={shipment.reload} />
          <PriorityCard shipmentId={s.id} priority={s.priority} onDone={shipment.reload} />
          <RiskCard shipmentId={s.id} isAtRisk={s.is_at_risk} riskReason={s.risk_reason} onDone={shipment.reload} />
          <RoutingCard shipmentId={s.id} carrier={s.carrier} voyageFlightNumber={s.voyage_flight_number} onDone={shipment.reload} />
          <ReferencesCard shipmentId={s.id} references={s.references} onDone={shipment.reload} />
          <DocumentsCard shipmentId={s.id} />
          {!s.is_cancelled && <CancelShipmentCard shipmentId={s.id} onDone={shipment.reload} />}
          <DeleteShipmentCard shipmentId={s.id} label={s.job_number ?? `Inquiry #${s.inquiry_id}`} />

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Shipment info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <InfoRow label="Inquiry received" value={formatDate(s.created_at)} />
              <InfoRow label="Last updated" value={formatDate(s.updated_at)} />
              {inquiry.data && <InfoRow label="Cargo" value={inquiry.data.cargo_type} />}
              {inquiry.data && <InfoRow label="Incoterm" value={inquiry.data.incoterm} />}
              {inquiry.data?.hs_code && <InfoRow label="HS Code" value={inquiry.data.hs_code} />}
              {inquiry.data?.pieces && <InfoRow label="Pieces" value={String(inquiry.data.pieces)} />}
              {inquiry.data?.supplier_name && <InfoRow label="Supplier" value={inquiry.data.supplier_name} />}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  )
}

// Mostly read-only: normal progression is worker-only, scoped to the area
// responsible for the shipment's next stage (see the worker portal at
// /worker/queue). The one exception is the final step, Invoice to Customer
// — a finance action with no physical location/worker area, so ops marks
// it directly here, the same way it always could via correction, but as a
// clean single-purpose action instead.
function NextStageCard({
  shipmentId,
  nextStage,
  onDone,
}: {
  shipmentId: number
  nextStage: { stage: ShipmentStage; label: string } | null
  onDone: () => void
}) {
  const areas = useAsync(() => areasApi.list(), [])
  const areaName = areas.data?.find((a) => a.stage === nextStage?.stage)?.name
  const [note, setNote] = useState("")
  const [submitting, setSubmitting] = useState(false)

  if (!nextStage) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 py-4 text-sm text-status-success">
          <CheckCircle size={18} weight="fill" />
          <span className="font-medium">Job complete — invoiced to customer.</span>
        </CardContent>
      </Card>
    )
  }

  if (nextStage.stage === "invoice_to_customer") {
    async function handleInvoice() {
      setSubmitting(true)
      try {
        await shipmentsApi.invoice(shipmentId, note.trim() || undefined)
        toast.success("Marked as invoiced")
        onDone()
      } catch (err) {
        toast.error(err instanceof ApiError ? err.message : "Could not mark this shipment invoiced.")
      } finally {
        setSubmitting(false)
      }
    }

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Next stage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Cargo has arrived. <span className="font-medium text-foreground">Invoice to Customer</span> is the
            final step — ops marks it directly since it isn't tied to a physical location.
          </p>
          <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note (optional)" rows={2} />
          <Button onClick={handleInvoice} disabled={submitting} className="w-full gap-1.5">
            <CheckCircle size={16} weight="fill" />
            {submitting ? "Marking invoiced…" : "Mark Invoiced"}
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Next stage</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <UsersThree size={18} className="mt-0.5 shrink-0" />
          <span>
            <span className="font-medium text-foreground">{nextStage.label}</span> — waiting for a worker
            {areaName ? (
              <>
                {" "}
                in <span className="font-medium text-foreground">{areaName}</span>
              </>
            ) : null}{" "}
            to mark it done.
          </span>
        </p>
      </CardContent>
    </Card>
  )
}

function CorrectionCard({
  shipmentId,
  currentStage,
  onDone,
}: {
  shipmentId: number
  currentStage: ShipmentStage
  onDone: () => void
}) {
  const { stages } = useStages()
  const [open, setOpen] = useState(false)
  const [stage, setStage] = useState<ShipmentStage | "">("")
  const [reason, setReason] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function handleCorrect() {
    if (!stage || !reason.trim()) return
    setSubmitting(true)
    try {
      await shipmentsApi.correctStatus(shipmentId, stage, reason.trim())
      toast.success("Status corrected")
      setOpen(false)
      setStage("")
      setReason("")
      onDone()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not correct status.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-1.5">
          <PencilSimple size={16} />
          Correct status
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Correct shipment status</DialogTitle>
          <DialogDescription>
            Use this to fix a mistake in the status history — for example, an update applied to the wrong
            stage. This creates a new event; nothing is deleted. A reason is required.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Correct stage to</Label>
            <Select value={stage} onValueChange={(v) => setStage(v as ShipmentStage)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a stage" />
              </SelectTrigger>
              <SelectContent>
                {stages
                  .filter((s) => s.stage !== currentStage)
                  .map((s) => (
                    <SelectItem key={s.stage} value={s.stage}>
                      {s.label}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="correction-reason">Reason (required)</Label>
            <Textarea
              id="correction-reason"
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why is this correction needed?"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleCorrect} disabled={submitting || !stage || !reason.trim()}>
            {submitting ? "Saving…" : "Apply correction"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

const PRIORITY_LABEL: Record<Priority, string> = { low: "Low", medium: "Medium", high: "High" }

function PriorityCard({
  shipmentId,
  priority,
  onDone,
}: {
  shipmentId: number
  priority: Priority
  onDone: () => void
}) {
  const [submitting, setSubmitting] = useState(false)

  async function handleChange(next: Priority) {
    if (next === priority) return
    setSubmitting(true)
    try {
      await shipmentsApi.setPriority(shipmentId, next)
      toast.success(`Priority set to ${PRIORITY_LABEL[next]}`)
      onDone()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update priority.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Priority</CardTitle>
      </CardHeader>
      <CardContent>
        <Select value={priority} onValueChange={(v) => handleChange(v as Priority)} disabled={submitting}>
          <SelectTrigger className="w-full" aria-label="Priority">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="low">Low</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="high">High</SelectItem>
          </SelectContent>
        </Select>
      </CardContent>
    </Card>
  )
}

function RoutingCard({
  shipmentId,
  carrier,
  voyageFlightNumber,
  onDone,
}: {
  shipmentId: number
  carrier: string | null
  voyageFlightNumber: string | null
  onDone: () => void
}) {
  const [carrierValue, setCarrierValue] = useState(carrier ?? "")
  const [voyageValue, setVoyageValue] = useState(voyageFlightNumber ?? "")
  const [saving, setSaving] = useState(false)

  const dirty = carrierValue !== (carrier ?? "") || voyageValue !== (voyageFlightNumber ?? "")

  async function handleSave() {
    setSaving(true)
    try {
      await shipmentsApi.setRouting(shipmentId, carrierValue.trim() || null, voyageValue.trim() || null)
      toast.success("Routing updated")
      onDone()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update routing.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Routing</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="carrier">Carrier / Airline</Label>
          <Input id="carrier" value={carrierValue} onChange={(e) => setCarrierValue(e.target.value)} placeholder="e.g. Emirates Airline" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="voyage-flight">Voyage / Flight No</Label>
          <Input id="voyage-flight" value={voyageValue} onChange={(e) => setVoyageValue(e.target.value)} placeholder="e.g. TG-0346" />
        </div>
        {dirty && (
          <Button size="sm" className="w-full" onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save routing"}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

function RiskCard({
  shipmentId,
  isAtRisk,
  riskReason,
  onDone,
}: {
  shipmentId: number
  isAtRisk: boolean
  riskReason: string | null
  onDone: () => void
}) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState(riskReason ?? "")
  const [submitting, setSubmitting] = useState(false)

  async function handleSetRisk(next: boolean) {
    if (next && !reason.trim()) return
    setSubmitting(true)
    try {
      await shipmentsApi.setRisk(shipmentId, next, next ? reason.trim() : undefined)
      toast.success(next ? "Marked at risk" : "Risk cleared")
      setOpen(false)
      onDone()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update risk status.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Risk status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {isAtRisk ? (
          <>
            <p className="rounded-lg bg-status-warning-bg px-3 py-2 text-sm text-status-warning">{riskReason}</p>
            <Button variant="outline" disabled={submitting} onClick={() => handleSetRisk(false)} className="w-full">
              {submitting ? "Updating…" : "Clear at-risk status"}
            </Button>
          </>
        ) : open ? (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="risk-reason">Why is this shipment at risk?</Label>
              <Textarea
                id="risk-reason"
                rows={2}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Carrier missed departure"
              />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                className="flex-1"
                disabled={submitting || !reason.trim()}
                onClick={() => handleSetRisk(true)}
              >
                {submitting ? "Saving…" : "Mark at risk"}
              </Button>
            </div>
          </>
        ) : (
          <Button variant="outline" className="w-full gap-1.5" onClick={() => setOpen(true)}>
            <Warning size={16} />
            Mark as at risk
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

function HoldCard({
  shipmentId,
  isOnHold,
  holdReason,
  onDone,
}: {
  shipmentId: number
  isOnHold: boolean
  holdReason: string | null
  onDone: () => void
}) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function handleSetHold(next: boolean) {
    setSubmitting(true)
    try {
      await shipmentsApi.setHold(shipmentId, next, next ? reason.trim() || undefined : undefined)
      toast.success(next ? "Shipment placed on hold" : "Hold removed")
      setOpen(false)
      setReason("")
      onDone()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update hold status.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Operational hold</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {isOnHold ? (
          <>
            {holdReason && <p className="rounded-lg bg-status-warning-bg px-3 py-2 text-sm text-status-warning">{holdReason}</p>}
            <p className="text-xs text-muted-foreground">Workers cannot advance this shipment while it's on hold.</p>
            <Button variant="outline" disabled={submitting} onClick={() => handleSetHold(false)} className="w-full gap-1.5">
              <PauseCircle size={16} />
              {submitting ? "Updating…" : "Remove hold"}
            </Button>
          </>
        ) : open ? (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="hold-reason">Why is this shipment on hold?</Label>
              <Textarea
                id="hold-reason"
                rows={2}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Missing customs document"
              />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button className="flex-1" disabled={submitting} onClick={() => handleSetHold(true)}>
                {submitting ? "Saving…" : "Place on hold"}
              </Button>
            </div>
          </>
        ) : (
          <Button variant="outline" className="w-full gap-1.5" onClick={() => setOpen(true)}>
            <PauseCircle size={16} />
            Place on hold
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

function CancelShipmentCard({ shipmentId, onDone }: { shipmentId: number; onDone: () => void }) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState("")
  const [customerNote, setCustomerNote] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function handleCancel() {
    if (!reason.trim()) return
    setSubmitting(true)
    try {
      await shipmentsApi.cancel(shipmentId, reason.trim(), customerNote.trim() || undefined)
      toast.success("Shipment cancelled")
      setOpen(false)
      onDone()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not cancel shipment.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="w-full gap-1.5 text-destructive hover:text-destructive">
          <Prohibit size={16} />
          Cancel shipment
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cancel shipment</DialogTitle>
          <DialogDescription>
            The shipment stays visible in history at its current stage — nothing is deleted. This cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="cancel-reason">Internal reason (required)</Label>
            <Textarea
              id="cancel-reason"
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Not shown to the customer"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cancel-customer-note">Customer-visible note (optional)</Label>
            <Textarea
              id="cancel-customer-note"
              rows={2}
              value={customerNote}
              onChange={(e) => setCustomerNote(e.target.value)}
              placeholder="Defaults to “Shipment cancelled.” if left blank"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Back
          </Button>
          <Button variant="destructive" onClick={handleCancel} disabled={submitting || !reason.trim()}>
            {submitting ? "Cancelling…" : "Cancel shipment"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DeleteShipmentCard({ shipmentId, label }: { shipmentId: number; label: string }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleDelete() {
    setSubmitting(true)
    try {
      await shipmentsApi.remove(shipmentId)
      toast.success(`${label} deleted`)
      navigate("/shipments")
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete shipment.")
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="w-full gap-1.5 text-destructive hover:text-destructive">
          <Trash size={16} />
          Delete shipment
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {label}?</DialogTitle>
          <DialogDescription>
            This permanently erases the shipment, its inquiry, every quote revision, documents, and status
            history — unlike Cancel, nothing is kept. Refused if any quote has an invoice; cancel first in that
            case. This cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={submitting}>
            Back
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={submitting}>
            {submitting ? "Deleting…" : "Delete permanently"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ReferencesCard({
  shipmentId,
  references,
  onDone,
}: {
  shipmentId: number
  references: { id: number; type: string; value: string }[]
  onDone: () => void
}) {
  const [type, setType] = useState<ReferenceType>("MAWB")
  const [value, setValue] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function handleAdd() {
    if (!value.trim()) return
    setSubmitting(true)
    try {
      await shipmentsApi.addReference(shipmentId, type, value.trim())
      toast.success("Reference added")
      setValue("")
      onDone()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not add reference.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">References</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {references.length > 0 ? (
          <ul className="space-y-1.5 text-sm">
            {references.map((r) => (
              <li key={r.id} className="flex items-center justify-between rounded-lg bg-muted px-3 py-1.5">
                <span className="text-muted-foreground">{r.type.replace("_", " ")}</span>
                <span className="font-medium tabular-nums">{r.value}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No additional references yet.</p>
        )}
        <Separator />
        <div className="flex gap-2">
          <Select value={type} onValueChange={(v) => setType(v as ReferenceType)}>
            <SelectTrigger className="w-28 shrink-0" aria-label="Reference type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {REFERENCE_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Reference number"
            aria-label="Reference value"
          />
        </div>
        <Button variant="outline" size="sm" disabled={submitting || !value.trim()} onClick={handleAdd} className="w-full">
          {submitting ? "Adding…" : "Add reference"}
        </Button>
      </CardContent>
    </Card>
  )
}
