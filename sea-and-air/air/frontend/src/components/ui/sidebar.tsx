import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { CaretLineLeft, CaretLineRight } from "@phosphor-icons/react"

// Plain, prop-driven -- no context. There is exactly one sidebar per portal
// shell (AppShell owns the collapsed state directly), so a provider/context
// here was solving a problem that didn't exist and made the collapsed
// styling depend on a Tailwind `group` ancestor class that was never
// actually applied, silently breaking the collapse-to-icon behavior.

// Desktop: fixed-width column, collapses to icon-only. Mobile (<768px): the
// caller renders this inside a Sheet instead (see AppShell) rather than this
// component owning a second overlay mode.
export function Sidebar({
  collapsed,
  className,
  children,
}: {
  collapsed: boolean
  className?: string
  children: React.ReactNode
}) {
  return (
    <aside
      className={cn(
        "sticky top-0 hidden h-dvh shrink-0 flex-col overflow-hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-[var(--motion-base)] ease-[var(--motion-ease)] md:flex",
        className,
      )}
      style={{ width: collapsed ? "var(--sidebar-width-icon)" : "var(--sidebar-width)" }}
    >
      {children}
    </aside>
  )
}

export function SidebarHeader({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("flex h-14 shrink-0 items-center gap-1 border-b border-sidebar-border px-3", className)}>
      {children}
    </div>
  )
}

export function SidebarContent({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("flex flex-1 flex-col gap-0.5 overflow-y-auto overflow-x-hidden p-2", className)}>{children}</div>
}

export function SidebarFooter({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("flex shrink-0 flex-col gap-1 border-t border-sidebar-border p-2", className)}>{children}</div>
}

export function SidebarTrigger({
  collapsed,
  onClick,
  className,
}: {
  collapsed: boolean
  onClick: () => void
  className?: string
}) {
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      className={cn("hidden shrink-0 md:inline-flex", className)}
      title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      onClick={onClick}
    >
      {collapsed ? <CaretLineRight size={16} /> : <CaretLineLeft size={16} />}
    </Button>
  )
}

// Content area next to the sidebar -- takes up the remaining width.
export function SidebarInset({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("flex min-h-dvh flex-1 flex-col", className)}>{children}</div>
}
