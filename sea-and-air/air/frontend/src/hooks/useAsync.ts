// One place that owns the load/error/data lifecycle for a fetch, so pages
// don't each re-implement their own loading/error state machine.

import { useCallback, useEffect, useState } from "react"
import { ApiError } from "@/lib/api/client"

interface AsyncState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [reloadToken, setReloadToken] = useState(0)

  const reload = useCallback(() => setReloadToken((t) => t + 1), [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fn()
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadToken])

  return { data, error, loading, reload }
}
