import { useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { CommandPalette, type CommandItemData } from "@/components/command/CommandPalette"
import { useAsync } from "@/hooks/useAsync"
import { useCustomerAuth } from "@/hooks/useCustomerAuth"
import { customerPortalApi } from "@/lib/api/client"

interface CustomerCommandPaletteProps {
  open: boolean
  onOpenChange: (v: boolean) => void
}

// Scoped strictly to this customer's own JWT-scoped shipments+quotes --
// mirrors exactly what customerPortalApi already exposes, no new calls.
export function CustomerCommandPalette({ open, onOpenChange }: CustomerCommandPaletteProps) {
  const navigate = useNavigate()
  const { token } = useCustomerAuth()
  const shipments = useAsync(() => customerPortalApi.shipments(token!), [token, open])
  const quotes = useAsync(() => customerPortalApi.quotes(token!), [token, open])

  const items = useMemo<CommandItemData[]>(() => {
    const shipmentItems: CommandItemData[] = (shipments.data ?? []).map((s) => ({
      id: `shipment-${s.id}`,
      label: s.job_number ?? `Shipment #${s.id}`,
      hint: `${s.origin} → ${s.destination}`,
      group: "Shipments",
      onSelect: () => navigate(`/customer/shipments/${s.id}`),
    }))
    const quoteItems: CommandItemData[] = (quotes.data ?? []).map((q) => ({
      id: `quote-${q.id}`,
      label: `Quote #${q.id}`,
      hint: q.status,
      group: "Quotes",
      onSelect: () => navigate(`/customer/quotes/${q.id}`),
    }))
    return [...shipmentItems, ...quoteItems]
  }, [shipments.data, quotes.data, navigate])

  return (
    <CommandPalette open={open} onOpenChange={onOpenChange} items={items} placeholder="Search your shipments, quotes…" />
  )
}
