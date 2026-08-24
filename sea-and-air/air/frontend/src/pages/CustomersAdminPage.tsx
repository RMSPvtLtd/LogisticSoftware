import { useState } from "react"
import { toast } from "sonner"
import { Key, UserCircle } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PasswordInput } from "@/components/ui/password-input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useAsync } from "@/hooks/useAsync"
import { customersApi, ApiError } from "@/lib/api/client"
import type { Customer } from "@/lib/api/types"

export function CustomersAdminPage() {
  const customers = useAsync(() => customersApi.list(), [])

  return (
    <div>
      <PageHeader
        title="Customers"
        description="Grant a portal login to higher-volume clients so they can track their own shipments and quotes."
      />

      {customers.loading && <LoadingState rows={4} />}
      {!customers.loading && customers.error && <ErrorState message={customers.error} onRetry={customers.reload} />}
      {!customers.loading && !customers.error && (customers.data?.length ?? 0) === 0 && (
        <EmptyState
          icon={<UserCircle size={32} />}
          title="No customers yet"
          description="Customers are created from the New Quote flow."
        />
      )}

      {!customers.loading && !customers.error && (customers.data?.length ?? 0) > 0 && (
        <div className="space-y-3">
          {customers.data!.map((customer) => (
            <CustomerRow key={customer.id} customer={customer} onChanged={customers.reload} />
          ))}
        </div>
      )}
    </div>
  )
}

function CustomerRow({ customer, onChanged }: { customer: Customer; onChanged: () => void }) {
  return (
    <Card>
      <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
        <div>
          <div className="flex items-center gap-2">
            <p className="font-heading text-sm font-semibold text-foreground">{customer.name}</p>
            {customer.company_name && <span className="text-sm text-muted-foreground">{customer.company_name}</span>}
          </div>
          <p className="text-xs text-muted-foreground">{customer.email}</p>
        </div>

        <div className="flex items-center gap-2">
          {customer.username ? (
            <>
              <Badge variant="outline" className="gap-1 text-[11px]">
                @{customer.username}
              </Badge>
              <PortalStatusToggle customer={customer} onChanged={onChanged} />
              <GrantAccessDialog customer={customer} onChanged={onChanged} resetting />
            </>
          ) : (
            <GrantAccessDialog customer={customer} onChanged={onChanged} resetting={false} />
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function PortalStatusToggle({ customer, onChanged }: { customer: Customer; onChanged: () => void }) {
  const [submitting, setSubmitting] = useState(false)

  async function handleToggle() {
    setSubmitting(true)
    try {
      await customersApi.setPortalActive(customer.id, !customer.portal_active)
      toast.success(customer.portal_active ? "Portal access disabled" : "Portal access enabled")
      onChanged()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update portal access.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Button
      variant={customer.portal_active ? "outline" : "secondary"}
      size="sm"
      disabled={submitting}
      onClick={handleToggle}
    >
      {customer.portal_active ? "Deactivate" : "Reactivate"}
    </Button>
  )
}

function GrantAccessDialog({
  customer,
  onChanged,
  resetting,
}: {
  customer: Customer
  onChanged: () => void
  resetting: boolean
}) {
  const [open, setOpen] = useState(false)
  const [username, setUsername] = useState(customer.username ?? "")
  const [password, setPassword] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const valid = username.trim().length >= 3 && password.length >= 6

  async function handleSubmit() {
    if (!valid) return
    setSubmitting(true)
    try {
      await customersApi.grantPortalAccess(customer.id, { username: username.trim(), password })
      toast.success(resetting ? "Portal password reset" : "Portal access granted")
      setPassword("")
      setOpen(false)
      onChanged()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not grant portal access.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={resetting ? "ghost" : "secondary"} size="sm" className="gap-1.5">
          <Key size={14} />
          {resetting ? "Reset password" : "Grant portal access"}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{resetting ? "Reset portal password" : "Grant portal access"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="customer-username">Username</Label>
            <Input
              id="customer-username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. orient.traders"
              disabled={resetting}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="customer-password">{resetting ? "New password" : "Temporary password"}</Label>
            <PasswordInput
              id="customer-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!valid || submitting}>
            {submitting ? "Saving…" : resetting ? "Reset password" : "Grant access"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
