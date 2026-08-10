import { Navigate } from "react-router-dom"
import type { ReactNode } from "react"
import { useWorkerAuth } from "@/hooks/useWorkerAuth"
import { LoadingState } from "@/components/shared/States"

export function ProtectedWorkerRoute({ children }: { children: ReactNode }) {
  const { worker, loading } = useWorkerAuth()

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <LoadingState rows={3} />
      </div>
    )
  }
  if (!worker) return <Navigate to="/worker/login" replace />
  return <>{children}</>
}
