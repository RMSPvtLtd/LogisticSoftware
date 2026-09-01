import { useState } from "react"
import { toast } from "sonner"
import { CalendarBlank, Plus, Trash } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useAsync } from "@/hooks/useAsync"
import { airlineSchedulesApi, ApiError } from "@/lib/api/client"
import { cn } from "@/lib/utils"
import type { AirlineSchedule, AirlineScheduleInput, DayOfWeek, TransportMode } from "@/lib/api/types"

const MODES: TransportMode[] = ["air", "sea", "road"]
const DAYS: { value: DayOfWeek; label: string }[] = [
  { value: "mon", label: "Mon" },
  { value: "tue", label: "Tue" },
  { value: "wed", label: "Wed" },
  { value: "thu", label: "Thu" },
  { value: "fri", label: "Fri" },
  { value: "sat", label: "Sat" },
  { value: "sun", label: "Sun" },
]

function emptyForm(): AirlineScheduleInput {
  return { airline_name: "", origin: "", destination: "", mode: "air", days_of_week: [], notes: null }
}

function toInput(s: AirlineSchedule): AirlineScheduleInput {
  return {
    airline_name: s.airline_name,
    origin: s.origin,
    destination: s.destination,
    mode: s.mode,
    days_of_week: s.days_of_week,
    notes: s.notes,
  }
}

export function AirlineSchedulesAdminPage() {
  const schedules = useAsync(() => airlineSchedulesApi.list(), [])

  return (
    <div>
      <PageHeader
        title="Flight Schedule"
        description="Reference list of which days each airline flies a lane. For ops planning only -- has no effect on quoting or pricing."
        action={<ScheduleFormDialog onSaved={schedules.reload} />}
      />

      {schedules.loading && <LoadingState rows={3} />}
      {!schedules.loading && schedules.error && <ErrorState message={schedules.error} onRetry={schedules.reload} />}
      {!schedules.loading && !schedules.error && (schedules.data?.length ?? 0) === 0 && (
        <EmptyState
          icon={<CalendarBlank size={32} />}
          title="No flight schedules yet"
          description="Add an airline's weekly schedule for a lane so ops can reference it when planning a shipment."
        />
      )}

      {!schedules.loading && !schedules.error && (schedules.data?.length ?? 0) > 0 && (
        <div className="space-y-3">
          {schedules.data!.map((s) => (
            <ScheduleRow key={s.id} schedule={s} onChanged={schedules.reload} />
          ))}
        </div>
      )}
    </div>
  )
}

function ScheduleRow({ schedule, onChanged }: { schedule: AirlineSchedule; onChanged: () => void }) {
  const [deleting, setDeleting] = useState(false)

  async function handleDelete() {
    if (!confirm(`Delete ${schedule.airline_name}'s ${schedule.origin} → ${schedule.destination} schedule?`)) return
    setDeleting(true)
    try {
      await airlineSchedulesApi.remove(schedule.id)
      toast.success("Schedule deleted")
      onChanged()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete schedule.")
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Card>
      <CardContent className="space-y-2 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <p className="font-heading text-sm font-semibold text-foreground">{schedule.airline_name}</p>
              <Badge variant="outline" className="text-[11px] uppercase">
                {schedule.mode}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              {schedule.origin} &rarr; {schedule.destination}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ScheduleFormDialog schedule={schedule} onSaved={onChanged} />
            <Button variant="outline" size="sm" disabled={deleting} onClick={handleDelete}>
              <Trash size={14} />
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {DAYS.map((d) => (
            <span
              key={d.value}
              className={cn(
                "rounded-md px-2 py-0.5 text-xs font-medium",
                schedule.days_of_week.includes(d.value)
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              )}
            >
              {d.label}
            </span>
          ))}
        </div>

        {schedule.notes && <p className="text-sm text-muted-foreground">{schedule.notes}</p>}
      </CardContent>
    </Card>
  )
}

function ScheduleFormDialog({ schedule, onSaved }: { schedule?: AirlineSchedule; onSaved: () => void }) {
  const editing = Boolean(schedule)
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState<AirlineScheduleInput>(schedule ? toInput(schedule) : emptyForm())

  function resetForm() {
    setForm(schedule ? toInput(schedule) : emptyForm())
  }

  function toggleDay(day: DayOfWeek) {
    setForm((f) => ({
      ...f,
      days_of_week: f.days_of_week.includes(day)
        ? f.days_of_week.filter((d) => d !== day)
        : [...f.days_of_week, day],
    }))
  }

  const valid = form.airline_name.trim() && form.origin.trim() && form.destination.trim() && form.days_of_week.length > 0

  async function handleSubmit() {
    if (!valid) return
    setSubmitting(true)
    try {
      const payload: AirlineScheduleInput = {
        ...form,
        airline_name: form.airline_name.trim(),
        origin: form.origin.trim(),
        destination: form.destination.trim(),
        notes: form.notes?.trim() || null,
      }
      if (editing && schedule) {
        await airlineSchedulesApi.update(schedule.id, payload)
        toast.success("Schedule updated")
      } else {
        await airlineSchedulesApi.create(payload)
        toast.success("Schedule created")
      }
      setOpen(false)
      onSaved()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save schedule.")
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
            New schedule
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit flight schedule" : "New flight schedule"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Airline</Label>
              <Input
                value={form.airline_name}
                onChange={(e) => setForm((f) => ({ ...f, airline_name: e.target.value }))}
                placeholder="e.g. PIA Cargo"
              />
            </div>
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
          </div>

          <div className="space-y-1.5">
            <Label>Days flown</Label>
            <div className="flex flex-wrap gap-1.5">
              {DAYS.map((d) => {
                const active = form.days_of_week.includes(d.value)
                return (
                  <button
                    key={d.value}
                    type="button"
                    onClick={() => toggleDay(d.value)}
                    className={cn(
                      "rounded-md border px-2.5 py-1 text-xs font-medium transition-colors",
                      active
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-transparent text-muted-foreground hover:bg-muted"
                    )}
                  >
                    {d.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Notes</Label>
            <Textarea
              rows={2}
              value={form.notes ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value || null }))}
              placeholder="Optional"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!valid || submitting}>
            {submitting ? "Saving…" : editing ? "Save changes" : "Create schedule"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
