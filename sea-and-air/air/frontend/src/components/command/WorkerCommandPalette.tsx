import { useMemo } from "react"
import { CommandPalette, type CommandItemData } from "@/components/command/CommandPalette"
import { useAsync } from "@/hooks/useAsync"
import { useWorkerAuth } from "@/hooks/useWorkerAuth"
import { workerPortalApi } from "@/lib/api/client"

interface WorkerCommandPaletteProps {
  open: boolean
  onOpenChange: (v: boolean) => void
}

// Scoped strictly to this worker's own JWT-scoped queue -- the same data
// WorkerQueuePage already fetches. No cross-worker/cross-area visibility.
export function WorkerCommandPalette({ open, onOpenChange }: WorkerCommandPaletteProps) {
  const { token } = useWorkerAuth()
  const queue = useAsync(() => workerPortalApi.queue(token!), [token, open])

  const items = useMemo<CommandItemData[]>(
    () =>
      (queue.data ?? []).map((item) => ({
        id: `queue-${item.id}`,
        label: item.job_number,
        hint: `${item.origin} → ${item.destination}`,
        group: "Waiting on you",
        onSelect: () => {
          document.getElementById(`queue-item-${item.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" })
        },
      })),
    [queue.data],
  )

  return <CommandPalette open={open} onOpenChange={onOpenChange} items={items} placeholder="Search your queue…" />
}
