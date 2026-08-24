import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useOpsAuth } from "@/hooks/useOpsAuth"
import { ApiError, opsAuthApi } from "@/lib/api/client"

export function ChangePasswordDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { logout } = useOpsAuth()
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const mismatch = newPassword.length > 0 && confirmPassword.length > 0 && newPassword !== confirmPassword

  function reset() {
    setCurrentPassword("")
    setNewPassword("")
    setConfirmPassword("")
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      toast.error("New password and confirmation do not match.")
      return
    }
    setSubmitting(true)
    try {
      await opsAuthApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_new_password: confirmPassword,
      })
      toast.success("Password changed. Please sign in again.")
      reset()
      onOpenChange(false)
      // The change already revoked this session's token server-side
      // (token_version bump) -- log out locally too so the UI matches.
      logout()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not change password.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) reset(); onOpenChange(next) }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change password</DialogTitle>
          <DialogDescription>
            Changing your password signs out every other active session using this account.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="current-password">Current password</Label>
            <Input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              autoFocus
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-password">New password</Label>
            <Input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              minLength={8}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm-password">Confirm new password</Label>
            <Input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
            />
            {mismatch && <p className="text-xs text-destructive">Passwords do not match.</p>}
          </div>
          <DialogFooter>
            <Button
              type="submit"
              disabled={submitting || !currentPassword || newPassword.length < 8 || mismatch}
            >
              {submitting ? "Changing…" : "Change password"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
