import { Outlet } from "react-router-dom"
import { Truck } from "@phosphor-icons/react"
import { ThemeToggle } from "@/components/shared/ThemeToggle"
import { PageTransition } from "@/components/shared/PageTransition"

// Deliberately spare -- no sidebar, no command palette. This route is
// anonymous (no login, no JWT); the backend has no public search endpoint
// and this app adds none, so unlike the three authenticated portals there
// is no data this page could safely let a visitor search across tenants.
// It still shares the same design tokens/motion so it reads as the same
// product as the rest of Raaziq.
export function PublicShell() {
  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex h-14 max-w-3xl items-center gap-2 px-4 sm:px-6">
          <Truck size={22} weight="fill" className="text-accent-foreground" />
          <span className="font-heading text-base font-semibold text-foreground">Raaziq</span>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6 sm:py-12">
        <PageTransition>
          <Outlet />
        </PageTransition>
      </main>
      <footer className="border-t border-border py-4">
        <p className="mx-auto max-w-3xl px-4 text-center text-xs text-muted-foreground sm:px-6">
          Need help with your shipment? Contact your Raaziq account manager.
        </p>
      </footer>
    </div>
  )
}
