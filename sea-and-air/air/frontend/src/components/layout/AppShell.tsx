import { useCallback, useState, type ReactNode } from "react"
import { NavLink, Outlet } from "react-router-dom"
import { MagnifyingGlass, SignOut, Truck } from "@phosphor-icons/react"
import { cn } from "@/lib/utils"
import { ThemeToggle } from "@/components/shared/ThemeToggle"
import { PageTransition } from "@/components/shared/PageTransition"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader, SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { useCommandPaletteShortcut } from "@/hooks/useCommandPaletteShortcut"
import type { AppShellNavItem } from "@/components/layout/nav-config"

interface AppShellProps {
  brandHref: string
  navItems: AppShellNavItem[]
  identityLabel?: string
  onLogout?: () => void
  commandPalette?: (ctx: { open: boolean; onOpenChange: (v: boolean) => void }) => ReactNode
  children?: ReactNode
}

function initials(label: string) {
  return label
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("")
}

function NavLinks({ navItems, onNavigate }: { navItems: AppShellNavItem[]; onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-0.5" aria-label="Primary">
      {navItems.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors duration-[var(--motion-fast)]",
              isActive
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
            )
          }
        >
          <Icon size={17} className="shrink-0" />
          <span className="truncate group-data-[collapsed=true]:hidden">{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

export function AppShell({ brandHref, navItems, identityLabel, onLogout, commandPalette, children }: AppShellProps) {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const togglePalette = useCallback(() => setPaletteOpen((v) => !v), [])
  useCommandPaletteShortcut(togglePalette)

  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader>
          <NavLink to={brandHref} className="flex items-center gap-2 font-heading text-base font-semibold text-sidebar-foreground">
            <Truck size={20} weight="fill" className="shrink-0 text-sidebar-accent-foreground" />
            <span className="truncate">Raaziq</span>
          </NavLink>
          <SidebarTrigger className="ml-auto" />
        </SidebarHeader>
        <SidebarContent>
          <NavLinks navItems={navItems} />
        </SidebarContent>
        <SidebarFooter>
          {identityLabel && (
            <div className="flex items-center gap-2 px-1 py-1">
              <Avatar className="size-7">
                <AvatarFallback>{initials(identityLabel)}</AvatarFallback>
              </Avatar>
              <span className="min-w-0 flex-1 truncate text-xs font-medium text-sidebar-foreground">{identityLabel}</span>
              {onLogout && (
                <Button variant="ghost" size="icon-sm" aria-label="Sign out" onClick={onLogout}>
                  <SignOut size={15} />
                </Button>
              )}
            </div>
          )}
          <div className="flex items-center justify-between px-1">
            <a
              href="/track"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium text-sidebar-foreground/70 transition-colors duration-[var(--motion-fast)] hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
            >
              <MagnifyingGlass size={14} />
              Customer tracking
            </a>
            <ThemeToggle />
          </div>
        </SidebarFooter>
      </Sidebar>

      {/* Mobile: sidebar content rendered inside the existing Sheet
          primitive instead of a second overlay implementation. */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-64 bg-sidebar text-sidebar-foreground">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2 font-heading">
              <Truck size={20} weight="fill" className="text-sidebar-accent-foreground" />
              Raaziq
            </SheetTitle>
          </SheetHeader>
          <div className="px-2">
            <NavLinks navItems={navItems} onNavigate={() => setMobileNavOpen(false)} />
          </div>
        </SheetContent>
      </Sheet>

      <SidebarInset>
        <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b border-border bg-card px-3 sm:px-4">
          <Button
            variant="ghost"
            size="icon-sm"
            className="md:hidden"
            aria-label="Open navigation"
            onClick={() => setMobileNavOpen(true)}
          >
            <Truck size={18} />
          </Button>
          <button
            type="button"
            onClick={togglePalette}
            className="ml-auto flex items-center gap-2 rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm text-muted-foreground transition-colors duration-[var(--motion-fast)] hover:border-ring hover:text-foreground"
          >
            <MagnifyingGlass size={15} />
            <span className="hidden sm:inline">Search…</span>
            <kbd className="hidden rounded border border-border bg-muted px-1.5 py-0.5 font-sans text-[0.65rem] text-muted-foreground sm:inline">
              ⌘K
            </kbd>
          </button>
        </header>
        <main className="flex-1 px-4 py-6 sm:px-6 sm:py-8">
          <PageTransition>{children ?? <Outlet />}</PageTransition>
        </main>
      </SidebarInset>

      {commandPalette?.({ open: paletteOpen, onOpenChange: setPaletteOpen })}
    </SidebarProvider>
  )
}
