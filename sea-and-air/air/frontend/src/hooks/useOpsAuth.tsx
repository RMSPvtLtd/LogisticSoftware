// Ops session state -- mirrors useWorkerAuth/useCustomerAuth exactly. The
// one difference: setOpsToken (lib/api/client) must be called alongside
// React state, since every ops-facing API call reads the token from that
// module-level variable rather than taking it as an explicit parameter (see
// client.ts's comment on why: dozens of ops call sites across nearly every
// ops page, vs. the worker/customer portals' much smaller surface).

import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { opsAuthApi, setOpsToken } from "@/lib/api/client"
import type { OpsUser } from "@/lib/api/types"

const TOKEN_STORAGE_KEY = "raaziq_ops_token"

interface OpsAuthContextValue {
  opsUser: OpsUser | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}

const OpsAuthContext = createContext<OpsAuthContextValue | null>(null)

export function OpsAuthProvider({ children }: { children: ReactNode }) {
  const [opsUser, setOpsUser] = useState<OpsUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (!stored) {
      setLoading(false)
      return
    }
    setOpsToken(stored)
    opsAuthApi
      .me()
      .then(setOpsUser)
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY)
        setOpsToken(null)
      })
      .finally(() => setLoading(false))
  }, [])

  async function login(username: string, password: string) {
    const result = await opsAuthApi.login(username, password)
    localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token)
    setOpsToken(result.access_token)
    setOpsUser(result.ops_user)
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    setOpsToken(null)
    setOpsUser(null)
  }

  async function refresh() {
    const user = await opsAuthApi.me()
    setOpsUser(user)
  }

  return (
    <OpsAuthContext.Provider value={{ opsUser, loading, login, logout, refresh }}>
      {children}
    </OpsAuthContext.Provider>
  )
}

export function useOpsAuth() {
  const ctx = useContext(OpsAuthContext)
  if (!ctx) throw new Error("useOpsAuth must be used within an OpsAuthProvider")
  return ctx
}
