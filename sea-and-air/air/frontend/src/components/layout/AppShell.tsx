import { useCallback, useState, type ReactNode } from "react"
import { NavLink, Outlet } from "react-router-dom"
import { ArrowSquareOut, MagnifyingGlass, SignOut, Truck } from "@phosphor-icons/react"
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
import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { useCommandPaletteShortcut } from "@/hooks/useCommandPaletteShortcut"
import type { AppShellNavItem } from "@/components/layout/nav-config"

const COLLAPSED_STORAGE_KEY = "raaziq.sidebar.collapsed"

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

function NavLinks({
  navItems,
  showLabels,
  onNavigate,
}: {
  navItems: AppShellNavItem[]
  showLabels: boolean
  onNavigate?: () => void
}) {
  return (
    <nav className="flex flex-col gap-0.5" aria-label="Primary">
      {navItems.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          onClick={onNavigate}
          title={showLabels ? undefined : label}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors duration-[var(--motion-fast)]",
              !showLabels && "justify-center",
              isActive
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
            )
          }
        >
          <Icon size={17} className="shrink-0" />
          {showLabels && <span className="truncate">{label}</span>}
        </NavLink>
      ))}
    </nav>
  )
}

export function AppShell({ brandHref, navItems, identityLabel, onLogout, commandPalette, children }: AppShellProps) {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(
    () => typeof window !== "undefined" && window.localStorage.getItem(COLLAPSED_STORAGE_KEY) === "1",
  )
  const togglePalette = useCallback(() => setPaletteOpen((v) => !v), [])
  useCommandPaletteShortcut(togglePalette)

  function toggleCollapsed() {
    setCollapsed((v) => {
      const next = !v
      window.localStorage.setItem(COLLAPSED_STORAGE_KEY, next ? "1" : "0")
      return next
    })
  }

  return (
    <div className="flex min-h-dvh w-full">
      <Sidebar collapsed={collapsed}>
        <SidebarHeader className={collapsed ? "justify-center" : undefined}>
          <NavLink
            to={brandHref}
            title="Raaziq"
            className="flex min-w-0 items-center gap-2 font-heading text-base font-semibold text-sidebar-foreground"
          >
            <Truck size={20} weight="fill" className="shrink-0 text-sidebar-accent-foreground" />
            {!collapsed && <span className="truncate">Raaziq</span>}
          </NavLink>
          {!collapsed && <SidebarTrigger collapsed={collapsed} onClick={toggleCollapsed} className="ml-auto" />}
        </SidebarHeader>
        <SidebarContent>
          <NavLinks navItems={navItems} showLabels={!collapsed} />
        </SidebarContent>
        <SidebarFooter className={collapsed ? "items-center" : undefined}>
          {identityLabel &&
            (collapsed ? (
              <div className="flex flex-col items-center gap-1.5 py-1">
                <Avatar className="size-7" title={identityLabel}>
                  <AvatarFallback>{initials(identityLabel)}</AvatarFallback>
                </Avatar>
                {onLogout && (
                  <Button variant="ghost" size="icon-sm" title="Sign out" aria-label="Sign out" onClick={onLogout}>
                    <SignOut size={15} />
                  </Button>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2 px-1 py-1">
                <Avatar className="size-7">
                  <AvatarFallback>{initials(identityLabel)}</AvatarFallback>
                </Avatar>
                <span className="min-w-0 flex-1 truncate text-xs font-medium text-sidebar-foreground">{identityLabel}</span>
                {onLogout && (
                  <Button variant="ghost" size="icon-sm" title="Sign out" aria-label="Sign out" onClick={onLogout}>
                    <SignOut size={15} />
                  </Button>
                )}
              </div>
            ))}

          {/* Utility row: always icon-only, so it never wraps or squeezes
              regardless of collapsed state -- this used to mix a text link
              with an icon button and look unbalanced. */}
          <div className={cn("flex items-center gap-1", collapsed ? "flex-col" : "justify-between")}>
            <a
              href="/track"
              target="_blank"
              rel="noreferrer"
              title="Open customer tracking (new tab)"
              className="flex size-8 items-center justify-center rounded-lg text-sidebar-foreground/70 transition-colors duration-[var(--motion-fast)] hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
            >
              <ArrowSquareOut size={16} />
            </a>
            <ThemeToggle />
            {collapsed && <SidebarTrigger collapsed={collapsed} onClick={toggleCollapsed} />}
          </div>
        </SidebarFooter>
      </Sidebar>

      {/* Mobile: sidebar content rendered inside the existing Sheet
          primitive instead of a second overlay implementation. Always shows
          labels -- desktop's collapsed state is irrelevant here. */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-64 bg-sidebar text-sidebar-foreground">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2 font-heading">
              <Truck size={20} weight="fill" className="text-sidebar-accent-foreground" />
              Raaziq
            </SheetTitle>
          </SheetHeader>
          <div className="px-2">
            <NavLinks navItems={navItems} showLabels onNavigate={() => setMobileNavOpen(false)} />
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
    </div>
  )
}
