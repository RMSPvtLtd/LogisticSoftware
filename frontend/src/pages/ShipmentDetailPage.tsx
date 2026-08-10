import { useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"
import { ArrowLeft, PencilSimple, UsersThree, Warning } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { StageBadge } from "@/components/shared/StageBadge"
import { RiskBadge } from "@/components/shared/RiskBadge"
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
import { useAsync } from "@/hooks/useAsync"
import { useStages } from "@/hooks/useStages"
import { areasApi, customersApi, inquiriesApi, shipmentsApi } from "@/lib/api/client"
import { ApiError } from "@/lib/api/client"
import { formatDate } from "@/lib/format"
import type { ReferenceType, ShipmentStage } from "@/lib/api/types"

const MODE_LABEL: Record<string, string> = { air: "Air", sea: "Sea", road: "Road" }
const REFERENCE_TYPES: ReferenceType[] = ["MAWB", "HAWB", "MBL", "HBL", "CONTAINER"]

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
            {s.job_number}
            <StageBadge stage={s.stage} />
            {s.is_at_risk && <RiskBadge />}
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
          <NextStageCard nextStage={nextStage} />
          <CorrectionCard shipmentId={s.id} currentStage={s.stage} onDone={shipment.reload} />
          <RiskCard shipmentId={s.id} isAtRisk={s.is_at_risk} riskReason={s.risk_reason} onDone={shipment.reload} />
          <ReferencesCard shipmentId={s.id} references={s.references} onDone={shipment.reload} />

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Shipment info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <InfoRow label="Job opened" value={formatDate(s.created_at)} />
              <InfoRow label="Last updated" value={formatDate(s.updated_at)} />
              {inquiry.data && <InfoRow label="Cargo" value={inquiry.data.cargo_type} />}
              {inquiry.data && <InfoRow label="Incoterm" value={inquiry.data.incoterm} />}
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

// Read-only: normal progression is worker-only now, scoped to the area
// responsible for the shipment's next stage (see the worker portal at
// /worker/queue). Ops does not advance shipments directly — only corrects
// mistakes, below.
function NextStageCard({ nextStage }: { nextStage: { stage: ShipmentStage; label: string } | null }) {
  const areas = useAsync(() => areasApi.list(), [])
  const areaName = areas.data?.find((a) => a.stage === nextStage?.stage)?.name

  if (!nextStage) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 py-4 text-sm text-status-success">
          <span className="font-medium">Shipment delivered — lifecycle complete.</span>
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
