import type { Icon } from "@phosphor-icons/react"
import { ClipboardText, House, Package, Plus, Receipt, UserCircle, Users } from "@phosphor-icons/react"

export interface AppShellNavItem {
  to: string
  label: string
  icon: Icon
}

export const OPS_NAV: AppShellNavItem[] = [
  { to: "/", label: "Overview", icon: House },
  { to: "/shipments", label: "Shipments", icon: Package },
  { to: "/quotes/new", label: "New Quote", icon: Plus },
  { to: "/workers", label: "Workers", icon: Users },
  { to: "/customers", label: "Customers", icon: UserCircle },
]

export const CUSTOMER_NAV: AppShellNavItem[] = [
  { to: "/customer/shipments", label: "Shipments", icon: Package },
  { to: "/customer/quotes", label: "Quotes", icon: Receipt },
]

export const WORKER_NAV: AppShellNavItem[] = [{ to: "/worker/queue", label: "Queue", icon: ClipboardText }]
