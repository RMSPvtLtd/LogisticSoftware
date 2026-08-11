import { NavLink, Outlet, useNavigate } from "react-router-dom"
import { Package, Receipt, SignOut, Truck } from "@phosphor-icons/react"
import { cn } from "@/lib/utils"
import { ThemeToggle } from "@/components/shared/ThemeToggle"
import { Button } from "@/components/ui/button"
import { useCustomerAuth } from "@/hooks/useCustomerAuth"

const NAV_LINKS = [
  { to: "/customer/shipments", label: "Shipments", icon: Package },
  { to: "/customer/quotes", label: "Quotes", icon: Receipt },
]

export function CustomerShell() {
  const { customer, logout } = useCustomerAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate("/customer/login")
  }

  return (
    <div className="min-h-dvh bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-card">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-3 sm:gap-6 sm:px-6">
          <NavLink
            to="/customer/shipments"
            className="flex shrink-0 items-center gap-2 font-heading text-base font-semibold text-foreground"
          >
            <Truck size={22} weight="fill" className="text-accent-foreground" />
            <span className="hidden sm:inline">Raaziq</span>
          </NavLink>
          <nav className="flex items-center gap-1" aria-label="Primary">
            {NAV_LINKS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                aria-label={label}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors sm:px-3",
                    isActive
                      ? "bg-secondary text-secondary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )
                }
              >
                <Icon size={16} />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            {customer && (
              <span className="hidden truncate text-sm text-muted-foreground sm:inline">{customer.name}</span>
            )}
            <ThemeToggle />
            <Button variant="ghost" size="icon" aria-label="Sign out" onClick={handleLogout}>
              <SignOut size={18} />
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  )
}
