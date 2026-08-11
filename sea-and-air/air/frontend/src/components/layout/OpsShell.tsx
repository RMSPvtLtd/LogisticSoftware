import { NavLink, Outlet } from "react-router-dom"
import { MagnifyingGlass, Package, Plus, Truck, UserCircle, Users } from "@phosphor-icons/react"
import { cn } from "@/lib/utils"
import { ThemeToggle } from "@/components/shared/ThemeToggle"

const NAV_LINKS = [
  { to: "/shipments", label: "Shipments", icon: Package },
  { to: "/quotes/new", label: "New Quote", icon: Plus },
  { to: "/workers", label: "Workers", icon: Users },
  { to: "/customers", label: "Customers", icon: UserCircle },
]

export function OpsShell() {
  return (
    <div className="min-h-dvh bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-card">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-2 px-3 sm:gap-6 sm:px-6">
          <NavLink
            to="/shipments"
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
            <a
              href="/track"
              target="_blank"
              rel="noreferrer"
              aria-label="Customer tracking"
              className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground sm:px-3"
            >
              <MagnifyingGlass size={16} />
              <span className="hidden sm:inline">Customer tracking</span>
            </a>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  )
}
