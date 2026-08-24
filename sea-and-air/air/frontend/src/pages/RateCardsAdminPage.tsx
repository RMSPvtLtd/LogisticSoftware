import { useState } from "react"
import { toast } from "sonner"
import { Plus, Scales, Trash } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useAsync } from "@/hooks/useAsync"
import { rateCardsApi, ApiError } from "@/lib/api/client"
import type {
  ChargeBasis,
  ChargeKind,
  RateCard,
  RateCardBreakInput,
  RateCardChargeInput,
  RateCardInput,
  TransportMode,
  UnitOfMeasure,
} from "@/lib/api/types"

const MODES: TransportMode[] = ["air", "sea", "road"]
const UNITS: UnitOfMeasure[] = ["per_kg", "per_cbm", "flat"]
const CHARGE_KINDS: ChargeKind[] = ["freight", "documentation", "customs", "pickup", "handling", "other"]
const CHARGE_BASES: ChargeBasis[] = ["flat", "per_kg", "percent_of_freight"]

const EMPTY_BREAK: RateCardBreakInput = {
  min_weight: null,
  max_weight: null,
  min_volume: null,
  max_volume: null,
  unit: "per_kg",
  rate: "",
  description: "",
}

const EMPTY_CHARGE: RateCardChargeInput = {
  kind: "documentation",
  description: "",
  basis: "flat",
  amount: "",
}

export function RateCardsAdminPage() {
  const rateCards = useAsync(() => rateCardsApi.list(), [])

  return (
    <div>
      <PageHeader
        title="Rate Cards"
        description="Lane pricing used to generate quotes. An inquiry with no matching rate card cannot be priced."
        action={<RateCardFormDialog onSaved={rateCards.reload} />}
      />

      {rateCards.loading && <LoadingState rows={3} />}
      {!rateCards.loading && rateCards.error && <ErrorState message={rateCards.error} onRetry={rateCards.reload} />}
      {!rateCards.loading && !rateCards.error && (rateCards.data?.length ?? 0) === 0 && (
        <EmptyState
          icon={<Scales size={32} />}
          title="No rate cards yet"
          description="Add a rate card for a lane before a quote can be generated for it."
        />
      )}

      {!rateCards.loading && !rateCards.error && (rateCards.data?.length ?? 0) > 0 && (
        <div className="space-y-3">
          {rateCards.data!.map((rc) => (
            <RateCardRow key={rc.id} rateCard={rc} onChanged={rateCards.reload} />
          ))}
        </div>
      )}
    </div>
  )
}

function RateCardRow({ rateCard, onChanged }: { rateCard: RateCard; onChanged: () => void }) {
  const [deleting, setDeleting] = useState(false)

  async function handleDelete() {
    if (!confirm(`Delete the ${rateCard.origin} → ${rateCard.destination} (${rateCard.mode}) rate card?`)) return
    setDeleting(true)
    try {
      await rateCardsApi.remove(rateCard.id)
      toast.success("Rate card deleted")
      onChanged()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete rate card.")
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Card>
      <CardContent className="space-y-3 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <p className="font-heading text-sm font-semibold text-foreground">
                {rateCard.origin} &rarr; {rateCard.destination}
              </p>
              <Badge variant="outline" className="text-[11px] uppercase">
                {rateCard.mode}
              </Badge>
              {rateCard.carrier && <span className="text-sm text-muted-foreground">{rateCard.carrier}</span>}
            </div>
            <p className="text-xs text-muted-foreground">
              Valid {rateCard.valid_from} &ndash; {rateCard.valid_until} &middot; {rateCard.currency}{" "}
              {rateCard.minimum_charge} minimum
            </p>
          </div>
          <div className="flex items-center gap-2">
            <RateCardFormDialog rateCard={rateCard} onSaved={onChanged} />
            <Button variant="outline" size="sm" disabled={deleting} onClick={handleDelete}>
              <Trash size={14} />
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <p className="text-xs font-medium text-muted-foreground">Breaks</p>
            <ul className="mt-1 space-y-0.5 text-sm text-foreground">
              {rateCard.breaks.map((b) => (
                <li key={b.id}>
                  {b.description || `${b.min_weight ?? "0"}–${b.max_weight ?? "∞"} ${b.unit}`}: {b.rate}{" "}
                  {rateCard.currency}
                </li>
              ))}
            </ul>
          </div>
          {rateCard.charges.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground">Charges</p>
              <ul className="mt-1 space-y-0.5 text-sm text-foreground">
                {rateCard.charges.map((c) => (
                  <li key={c.id}>
                    {c.description}: {c.amount} {c.basis === "percent_of_freight" ? "%" : rateCard.currency}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function toInput(rc: RateCard): RateCardInput {
  return {
    origin: rc.origin,
    destination: rc.destination,
    mode: rc.mode,
    carrier: rc.carrier,
    currency: rc.currency,
    valid_from: rc.valid_from,
    valid_until: rc.valid_until,
    minimum_charge: rc.minimum_charge,
    breaks: rc.breaks.map((b) => ({
      min_weight: b.min_weight,
      max_weight: b.max_weight,
      min_volume: b.min_volume,
      max_volume: b.max_volume,
      unit: b.unit,
      rate: b.rate,
      description: b.description,
    })),
    charges: rc.charges.map((c) => ({ kind: c.kind, description: c.description, basis: c.basis, amount: c.amount })),
  }
}

function RateCardFormDialog({ rateCard, onSaved }: { rateCard?: RateCard; onSaved: () => void }) {
  const editing = Boolean(rateCard)
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const [form, setForm] = useState<RateCardInput>(
    rateCard
      ? toInput(rateCard)
      : {
          origin: "",
          destination: "",
          mode: "air",
          carrier: null,
          currency: "USD",
          valid_from: new Date().toISOString().slice(0, 10),
          valid_until: "",
          minimum_charge: "",
          breaks: [EMPTY_BREAK],
          charges: [],
        }
  )

  function resetForm() {
    setForm(
      rateCard
        ? toInput(rateCard)
        : {
            origin: "",
            destination: "",
            mode: "air",
            carrier: null,
            currency: "USD",
            valid_from: new Date().toISOString().slice(0, 10),
            valid_until: "",
            minimum_charge: "",
            breaks: [EMPTY_BREAK],
            charges: [],
          }
    )
  }

  const valid =
    form.origin.trim() &&
    form.destination.trim() &&
    form.currency.trim().length === 3 &&
    form.valid_from &&
    form.valid_until &&
    form.minimum_charge.trim() &&
    form.breaks.length > 0 &&
    form.breaks.every((b) => b.rate.trim() && b.unit) &&
    form.charges.every((c) => c.description.trim() && c.amount.trim())

  function updateBreak(index: number, patch: Partial<RateCardBreakInput>) {
    setForm((f) => ({ ...f, breaks: f.breaks.map((b, i) => (i === index ? { ...b, ...patch } : b)) }))
  }

  function updateCharge(index: number, patch: Partial<RateCardChargeInput>) {
    setForm((f) => ({ ...f, charges: f.charges.map((c, i) => (i === index ? { ...c, ...patch } : c)) }))
  }

  async function handleSubmit() {
    if (!valid) return
    setSubmitting(true)
    try {
      const payload: RateCardInput = {
        ...form,
        origin: form.origin.trim(),
        destination: form.destination.trim(),
        carrier: form.carrier?.trim() || null,
        currency: form.currency.trim().toUpperCase(),
      }
      if (editing && rateCard) {
        await rateCardsApi.update(rateCard.id, payload)
        toast.success("Rate card updated")
      } else {
        await rateCardsApi.create(payload)
        toast.success("Rate card created")
      }
      setOpen(false)
      onSaved()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save rate card.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (next) resetForm()
      }}
    >
      <DialogTrigger asChild>
        {editing ? (
          <Button variant="outline" size="sm">
            Edit
          </Button>
        ) : (
          <Button size="sm" className="gap-1.5">
            <Plus size={14} />
            New rate card
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit rate card" : "New rate card"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Origin</Label>
              <Input value={form.origin} onChange={(e) => setForm((f) => ({ ...f, origin: e.target.value }))} placeholder="e.g. Lahore" />
            </div>
            <div className="space-y-1.5">
              <Label>Destination</Label>
              <Input
                value={form.destination}
                onChange={(e) => setForm((f) => ({ ...f, destination: e.target.value }))}
                placeholder="e.g. London"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Mode</Label>
              <Select value={form.mode} onValueChange={(v) => setForm((f) => ({ ...f, mode: v as TransportMode }))}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MODES.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Carrier</Label>
              <Input
                value={form.carrier ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, carrier: e.target.value || null }))}
                placeholder="Optional"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Currency</Label>
              <Input
                value={form.currency}
                maxLength={3}
                onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value.toUpperCase() }))}
                placeholder="USD"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Minimum charge</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={form.minimum_charge}
                onChange={(e) => setForm((f) => ({ ...f, minimum_charge: e.target.value }))}
                placeholder="0.00"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Valid from</Label>
              <Input type="date" value={form.valid_from} onChange={(e) => setForm((f) => ({ ...f, valid_from: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <Label>Valid until</Label>
              <Input type="date" value={form.valid_until} onChange={(e) => setForm((f) => ({ ...f, valid_until: e.target.value }))} />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Weight/volume breaks</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setForm((f) => ({ ...f, breaks: [...f.breaks, EMPTY_BREAK] }))}
              >
                <Plus size={14} />
              </Button>
            </div>
            {form.breaks.map((b, i) => (
              <div key={i} className="grid grid-cols-2 gap-2 rounded-md border border-border p-2 sm:grid-cols-6">
                <Input
                  placeholder="Min kg"
                  value={b.min_weight ?? ""}
                  onChange={(e) => updateBreak(i, { min_weight: e.target.value || null })}
                />
                <Input
                  placeholder="Max kg"
                  value={b.max_weight ?? ""}
                  onChange={(e) => updateBreak(i, { max_weight: e.target.value || null })}
                />
                <Select value={b.unit} onValueChange={(v) => updateBreak(i, { unit: v as UnitOfMeasure })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {UNITS.map((u) => (
                      <SelectItem key={u} value={u}>
                        {u}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input placeholder="Rate" value={b.rate} onChange={(e) => updateBreak(i, { rate: e.target.value })} />
                <Input
                  placeholder="Description"
                  className="col-span-2"
                  value={b.description ?? ""}
                  onChange={(e) => updateBreak(i, { description: e.target.value || null })}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="col-span-2 justify-self-start sm:col-span-6"
                  disabled={form.breaks.length <= 1}
                  onClick={() => setForm((f) => ({ ...f, breaks: f.breaks.filter((_, idx) => idx !== i) }))}
                >
                  <Trash size={14} className="mr-1" /> Remove break
                </Button>
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Accessory charges</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setForm((f) => ({ ...f, charges: [...f.charges, EMPTY_CHARGE] }))}
              >
                <Plus size={14} />
              </Button>
            </div>
            {form.charges.map((c, i) => (
              <div key={i} className="grid grid-cols-2 gap-2 rounded-md border border-border p-2 sm:grid-cols-6">
                <Select value={c.kind} onValueChange={(v) => updateCharge(i, { kind: v as ChargeKind })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CHARGE_KINDS.map((k) => (
                      <SelectItem key={k} value={k}>
                        {k}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  placeholder="Description"
                  className="col-span-2"
                  value={c.description}
                  onChange={(e) => updateCharge(i, { description: e.target.value })}
                />
                <Select value={c.basis} onValueChange={(v) => updateCharge(i, { basis: v as ChargeBasis })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CHARGE_BASES.map((b) => (
                      <SelectItem key={b} value={b}>
                        {b}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input placeholder="Amount" value={c.amount} onChange={(e) => updateCharge(i, { amount: e.target.value })} />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="col-span-2 justify-self-start sm:col-span-6"
                  onClick={() => setForm((f) => ({ ...f, charges: f.charges.filter((_, idx) => idx !== i) }))}
                >
                  <Trash size={14} className="mr-1" /> Remove charge
                </Button>
              </div>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!valid || submitting}>
            {submitting ? "Saving…" : editing ? "Save changes" : "Create rate card"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
