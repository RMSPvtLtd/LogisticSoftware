import { Navigate } from "react-router-dom"
import type { ReactNode } from "react"
import { useOpsAuth } from "@/hooks/useOpsAuth"
import { LoadingState } from "@/components/shared/States"

export function ProtectedOpsRoute({ children }: { children: ReactNode }) {
  const { opsUser, loading } = useOpsAuth()

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <LoadingState rows={3} />
      </div>
    )
  }
  if (!opsUser) return <Navigate to="/login" replace />
  return <>{children}</>
}
