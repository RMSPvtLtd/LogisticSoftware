import { Outlet } from "react-router-dom"
import { Truck } from "@phosphor-icons/react"
import { ThemeToggle } from "@/components/shared/ThemeToggle"

// Deliberately spare -- no ops navigation, no internal terminology. This is
// the only screen an external customer ever sees.
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
        <Outlet />
      </main>
      <footer className="border-t border-border py-4">
        <p className="mx-auto max-w-3xl px-4 text-center text-xs text-muted-foreground sm:px-6">
          Need help with your shipment? Contact your Raaziq account manager.
        </p>
      </footer>
    </div>
  )
}
