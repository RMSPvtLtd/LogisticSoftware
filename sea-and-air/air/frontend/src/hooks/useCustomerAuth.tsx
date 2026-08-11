// Customer portal session state -- mirrors useWorkerAuth.tsx exactly, but
// with its own localStorage key so a worker session and a customer session
// can coexist in the same browser without clobbering each other.

import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { customerAuthApi } from "@/lib/api/client"
import type { Customer } from "@/lib/api/types"

const TOKEN_STORAGE_KEY = "raaziq_customer_token"

interface CustomerAuthContextValue {
  customer: Customer | null
  token: string | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const CustomerAuthContext = createContext<CustomerAuthContextValue | null>(null)

export function CustomerAuthProvider({ children }: { children: ReactNode }) {
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (!stored) {
      setLoading(false)
      return
    }
    customerAuthApi
      .me(stored)
      .then((c) => {
        setToken(stored)
        setCustomer(c)
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY)
      })
      .finally(() => setLoading(false))
  }, [])

  async function login(username: string, password: string) {
    const result = await customerAuthApi.login(username, password)
    localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token)
    setToken(result.access_token)
    setCustomer(result.customer)
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    setToken(null)
    setCustomer(null)
  }

  return (
    <CustomerAuthContext.Provider value={{ customer, token, loading, login, logout }}>
      {children}
    </CustomerAuthContext.Provider>
  )
}

export function useCustomerAuth() {
  const ctx = useContext(CustomerAuthContext)
  if (!ctx) throw new Error("useCustomerAuth must be used within a CustomerAuthProvider")
  return ctx
}
