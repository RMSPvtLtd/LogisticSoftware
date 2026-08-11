import { NavLink, Outlet } from "react-router-dom"
import { Anchor } from "@phosphor-icons/react"
import { cn } from "@/lib/utils"
import { ThemeToggle } from "@/components/shared/ThemeToggle"

// Deliberately a single "Track" tab today -- this nav is where future sea
// vertical sections (Quotes, Shipments, ...) would be added as the sea
// vertical grows, mirroring the shape of the air vertical's OpsShell
// without pulling in any of its air-specific tabs.
const NAV_LINKS = [{ to: "/track", label: "Track" }]

export function SeaShell() {
  return (
    <div className="min-h-dvh bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-card">
        <div className="mx-auto flex h-14 max-w-3xl items-center gap-2 px-4 sm:gap-6 sm:px-6">
          <NavLink
            to="/track"
            className="flex shrink-0 items-center gap-2 font-heading text-base font-semibold text-foreground"
          >
            <Anchor size={22} weight="fill" className="text-accent-foreground" />
            <span>Raaziq Sea</span>
          </NavLink>
          <nav className="flex items-center gap-1" aria-label="Primary">
            {NAV_LINKS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors sm:px-3",
                    isActive
                      ? "bg-secondary text-secondary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
        <Outlet />
      </main>
    </div>
  )
}
