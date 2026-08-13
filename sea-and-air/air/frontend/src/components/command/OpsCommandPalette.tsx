import { useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { CommandPalette, type CommandItemData } from "@/components/command/CommandPalette"
import { useAsync } from "@/hooks/useAsync"
import { customersApi, shipmentsApi, workersApi } from "@/lib/api/client"

interface OpsCommandPaletteProps {
  open: boolean
  onOpenChange: (v: boolean) => void
}

// Ops has no login/authorization boundary today (X-Actor header only), so
// this searches everything ops can already see via the existing endpoints
// -- no new backend calls beyond what OpsShell would fetch anyway.
export function OpsCommandPalette({ open, onOpenChange }: OpsCommandPaletteProps) {
  const navigate = useNavigate()
  const shipments = useAsync(() => shipmentsApi.list(), [open])
  const customers = useAsync(() => customersApi.list(), [open])
  const workers = useAsync(() => workersApi.list(), [open])

  const items = useMemo<CommandItemData[]>(() => {
    const shipmentItems: CommandItemData[] = (shipments.data ?? []).map((s) => ({
      id: `shipment-${s.id}`,
      label: s.job_number ?? `Shipment #${s.id}`,
      hint: s.stage.replace(/_/g, " "),
      group: "Shipments",
      onSelect: () => navigate(`/shipments/${s.id}`),
    }))
    const customerItems: CommandItemData[] = (customers.data ?? []).map((c) => ({
      id: `customer-${c.id}`,
      label: c.name,
      hint: c.company_name ?? undefined,
      group: "Customers",
      onSelect: () => navigate("/customers"),
    }))
    const workerItems: CommandItemData[] = (workers.data ?? []).map((w) => ({
      id: `worker-${w.id}`,
      label: w.name,
      hint: w.area.name,
      group: "Workers",
      onSelect: () => navigate("/workers"),
    }))
    return [...shipmentItems, ...customerItems, ...workerItems]
  }, [shipments.data, customers.data, workers.data, navigate])

  return (
    <CommandPalette
      open={open}
      onOpenChange={onOpenChange}
      items={items}
      placeholder="Search shipments, customers, workers…"
    />
  )
}
