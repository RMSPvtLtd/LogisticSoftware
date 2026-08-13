import { createContext, useContext, useState } from "react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { CaretLineLeft, CaretLineRight } from "@phosphor-icons/react"

const STORAGE_KEY = "raaziq.sidebar.collapsed"

interface SidebarContextValue {
  collapsed: boolean
  setCollapsed: (v: boolean) => void
}

const SidebarContext = createContext<SidebarContextValue | null>(null)

export function useSidebar() {
  const ctx = useContext(SidebarContext)
  if (!ctx) throw new Error("useSidebar must be used within a SidebarProvider")
  return ctx
}

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsedState] = useState(() => {
    if (typeof window === "undefined") return false
    return window.localStorage.getItem(STORAGE_KEY) === "1"
  })

  function setCollapsed(v: boolean) {
    setCollapsedState(v)
    window.localStorage.setItem(STORAGE_KEY, v ? "1" : "0")
  }

  return (
    <SidebarContext.Provider value={{ collapsed, setCollapsed }}>
      <div
        className="flex min-h-dvh w-full"
        style={
          {
            "--current-sidebar-width": collapsed
              ? "var(--sidebar-width-icon)"
              : "var(--sidebar-width)",
          } as React.CSSProperties
        }
      >
        {children}
      </div>
    </SidebarContext.Provider>
  )
}

// Desktop: fixed-width column, collapses to icon-only. Mobile (<768px): the
// caller renders this inside a Sheet instead (see AppShell) rather than this
// component owning a second overlay mode.
export function Sidebar({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  const { collapsed } = useSidebar()
  return (
    <aside
      data-collapsed={collapsed}
      className={cn(
        "sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-[var(--motion-base)] ease-[var(--motion-ease)] md:flex",
        className
      )}
      style={{ width: "var(--current-sidebar-width)" }}
    >
      {children}
    </aside>
  )
}

export function SidebarHeader({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("flex h-14 shrink-0 items-center border-b border-sidebar-border px-3", className)}>
      {children}
    </div>
  )
}

export function SidebarContent({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("flex flex-1 flex-col gap-0.5 overflow-y-auto p-2", className)}>{children}</div>
}

export function SidebarFooter({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("flex shrink-0 flex-col gap-1 border-t border-sidebar-border p-2", className)}>{children}</div>
}

export function SidebarTrigger({ className }: { className?: string }) {
  const { collapsed, setCollapsed } = useSidebar()
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      className={cn("hidden md:inline-flex", className)}
      aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      onClick={() => setCollapsed(!collapsed)}
    >
      {collapsed ? <CaretLineRight size={16} /> : <CaretLineLeft size={16} />}
    </Button>
  )
}

// Content area next to the sidebar -- takes up the remaining width.
export function SidebarInset({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("flex min-h-dvh flex-1 flex-col", className)}>{children}</div>
}
