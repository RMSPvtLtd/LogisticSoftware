// Worker portal session state: the token lives in localStorage so a worker
// stays logged in across reloads on their device; on mount we re-verify it
// against GET /auth/me rather than trusting the stored value blindly, since
// it may have expired or the account may have been deactivated since.

import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { authApi } from "@/lib/api/client"
import type { Worker } from "@/lib/api/types"

const TOKEN_STORAGE_KEY = "raaziq_worker_token"

interface WorkerAuthContextValue {
  worker: Worker | null
  token: string | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const WorkerAuthContext = createContext<WorkerAuthContextValue | null>(null)

export function WorkerAuthProvider({ children }: { children: ReactNode }) {
  const [worker, setWorker] = useState<Worker | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (!stored) {
      setLoading(false)
      return
    }
    authApi
      .me(stored)
      .then((w) => {
        setToken(stored)
        setWorker(w)
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY)
      })
      .finally(() => setLoading(false))
  }, [])

  async function login(username: string, password: string) {
    const result = await authApi.login(username, password)
    localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token)
    setToken(result.access_token)
    setWorker(result.worker)
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    setToken(null)
    setWorker(null)
  }

  return (
    <WorkerAuthContext.Provider value={{ worker, token, loading, login, logout }}>
      {children}
    </WorkerAuthContext.Provider>
  )
}

export function useWorkerAuth() {
  const ctx = useContext(WorkerAuthContext)
  if (!ctx) throw new Error("useWorkerAuth must be used within a WorkerAuthProvider")
  return ctx
}
