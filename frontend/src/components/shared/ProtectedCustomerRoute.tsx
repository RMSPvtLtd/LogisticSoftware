import { Navigate } from "react-router-dom"
import type { ReactNode } from "react"
import { useCustomerAuth } from "@/hooks/useCustomerAuth"
import { LoadingState } from "@/components/shared/States"

export function ProtectedCustomerRoute({ children }: { children: ReactNode }) {
  const { customer, loading } = useCustomerAuth()

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <LoadingState rows={3} />
      </div>
    )
  }
  if (!customer) return <Navigate to="/customer/login" replace />
  return <>{children}</>
}
