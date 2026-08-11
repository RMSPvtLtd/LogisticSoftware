import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { Airplane } from "@phosphor-icons/react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { useAsync } from "@/hooks/useAsync"
import { customersApi, inquiriesApi, quotesApi } from "@/lib/api/client"
import { ApiError } from "@/lib/api/client"

const INCOTERMS = ["EXW", "FOB", "CFR", "DAP", "DDP"] as const

// Raaziq currently only quotes air freight -- the backend's TransportMode
// still supports sea/road for later, but this form doesn't offer them.
const MODE = "air" as const

export function InquiryForm() {
  const navigate = useNavigate()
  const customers = useAsync(() => customersApi.list(), [])

  const [customerMode, setCustomerMode] = useState<"existing" | "new">("existing")
  const [customerId, setCustomerId] = useState<string>("")
  const [newName, setNewName] = useState("")
  const [newCompany, setNewCompany] = useState("")
  const [newEmail, setNewEmail] = useState("")
  const [newPhone, setNewPhone] = useState("")

  const [origin, setOrigin] = useState("")
  const [destination, setDestination] = useState("")
  const [cargoType, setCargoType] = useState("")
  const [weightKg, setWeightKg] = useState("")
  const [volumeCbm, setVolumeCbm] = useState("")
  const [dimensions, setDimensions] = useState("")
  const [incoterm, setIncoterm] = useState<string>("DAP")
  const [readyDate, setReadyDate] = useState("")
  const [description, setDescription] = useState("")

  const [submitting, setSubmitting] = useState(false)

  const customerValid = customerMode === "existing" ? Boolean(customerId) : Boolean(newName.trim() && newEmail.trim())
  const formValid =
    customerValid &&
    origin.trim() &&
    destination.trim() &&
    cargoType.trim() &&
    Number(weightKg) > 0 &&
    Number(volumeCbm) > 0 &&
    incoterm

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!formValid || submitting) return
    setSubmitting(true)
    try {
      let resolvedCustomerId: number
      if (customerMode === "existing") {
        resolvedCustomerId = Number(customerId)
      } else {
        const created = await customersApi.create({
          name: newName.trim(),
          company_name: newCompany.trim() || null,
          email: newEmail.trim(),
          phone: newPhone.trim() || null,
        })
        resolvedCustomerId = created.id
      }

      const inquiry = await inquiriesApi.create({
        customer_id: resolvedCustomerId,
        origin: origin.trim(),
        destination: destination.trim(),
        mode: MODE,
        cargo_type: cargoType.trim(),
        weight_kg: weightKg,
        volume_cbm: volumeCbm,
        dimensions: dimensions.trim() || null,
        incoterm,
        ready_date: readyDate || null,
        description: description.trim() || null,
      })

      const quote = await quotesApi.generate(inquiry.id)
      toast.success("Quote generated")
      navigate(`/quotes/${quote.id}`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not generate a quote.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Customer</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              type="button"
              variant={customerMode === "existing" ? "secondary" : "outline"}
              size="sm"
              onClick={() => setCustomerMode("existing")}
            >
              Existing customer
            </Button>
            <Button
              type="button"
              variant={customerMode === "new" ? "secondary" : "outline"}
              size="sm"
              onClick={() => setCustomerMode("new")}
            >
              New customer
            </Button>
          </div>

          {customerMode === "existing" ? (
            <div className="space-y-1.5">
              <Label>Select customer</Label>
              <Select value={customerId} onValueChange={setCustomerId}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={customers.loading ? "Loading customers…" : "Choose a customer"} />
                </SelectTrigger>
                <SelectContent>
                  {(customers.data ?? []).map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.name} {c.company_name ? `· ${c.company_name}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Name" required>
                <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Contact name" />
              </Field>
              <Field label="Company">
                <Input value={newCompany} onChange={(e) => setNewCompany(e.target.value)} placeholder="Company name" />
              </Field>
              <Field label="Email" required>
                <Input type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="name@company.com" />
              </Field>
              <Field label="Phone">
                <Input value={newPhone} onChange={(e) => setNewPhone(e.target.value)} placeholder="+92-..." />
              </Field>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Shipment details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Origin" required>
              <Input value={origin} onChange={(e) => setOrigin(e.target.value)} placeholder="e.g. Lahore" />
            </Field>
            <Field label="Destination" required>
              <Input value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="e.g. Dubai" />
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field label="Mode">
              <div className="flex h-9 items-center gap-1.5 rounded-lg border border-input bg-muted px-3 text-sm text-muted-foreground">
                <Airplane size={16} />
                Air Freight
              </div>
            </Field>
            <Field label="Cargo type" required>
              <Input value={cargoType} onChange={(e) => setCargoType(e.target.value)} placeholder="e.g. Garments" />
            </Field>
            <Field label="Incoterm" required>
              <Select value={incoterm} onValueChange={setIncoterm}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {INCOTERMS.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field label="Weight (kg)" required>
              <Input type="number" min="0.01" step="0.01" value={weightKg} onChange={(e) => setWeightKg(e.target.value)} placeholder="0.00" />
            </Field>
            <Field label="Volume (CBM)" required>
              <Input type="number" min="0.001" step="0.001" value={volumeCbm} onChange={(e) => setVolumeCbm(e.target.value)} placeholder="0.000" />
            </Field>
            <Field label="Ready date">
              <Input type="date" value={readyDate} onChange={(e) => setReadyDate(e.target.value)} />
            </Field>
          </div>

          <Field label="Dimensions">
            <Input value={dimensions} onChange={(e) => setDimensions(e.target.value)} placeholder="e.g. 120 x 80 x 100 cm" />
          </Field>

          <Field label="Notes">
            <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Anything else worth noting on this inquiry" />
          </Field>
        </CardContent>
      </Card>

      <Separator />

      <div className="flex justify-end">
        <Button type="submit" size="lg" disabled={!formValid || submitting} className="gap-1.5">
          {submitting ? "Generating quote…" : "Generate Quote"}
        </Button>
      </div>
    </form>
  )
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      {children}
    </div>
  )
}
