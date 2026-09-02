import { useState, type ComponentType } from "react"
import { NavLink, Outlet } from "react-router-dom"
import { CalendarBlank, Key, List, MagnifyingGlass, Package, Plus, Receipt, Scales, SignOut, Truck, UserCircle, Users } from "@phosphor-icons/react"
import { cn } from "@/lib/utils"
import { ThemeToggle } from "@/components/shared/ThemeToggle"
import { ChangePasswordDialog } from "@/components/shared/ChangePasswordDialog"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Sheet, SheetClose, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { useOpsAuth } from "@/hooks/useOpsAuth"

type Icon = ComponentType<{ size?: number; weight?: "regular" | "fill" | "duotone"; className?: string }>

const NAV_GROUPS: { label: string; links: { to: string; label: string; icon: Icon }[] }[] = [
  { label: "Control Tower", links: [{ to: "/overview", label: "Overview", icon: List }, { to: "/shipments", label: "Shipments", icon: Package }] },
  { label: "Commercial", links: [{ to: "/quotes/new", label: "Quotes", icon: Receipt }, { to: "/rate-cards", label: "Rate Cards", icon: Scales }, { to: "/airline-schedules", label: "Airline Schedules", icon: CalendarBlank }, { to: "/invoices", label: "Invoices", icon: Receipt }] },
  { label: "Network", links: [{ to: "/customers", label: "Customers", icon: UserCircle }, { to: "/workers", label: "Workers", icon: Users }] },
]

function SidebarNav({ closeOnNavigate = false }: { closeOnNavigate?: boolean }) {
  return (
    <nav className="space-y-5" aria-label="Operations navigation">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="mb-1.5 px-3 text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{group.label}</p>
          <div className="space-y-0.5">
            {group.links.map(({ to, label, icon: Icon }) => {
              const link = <NavLink to={to} end={to === "/overview" || to === "/shipments" || to === "/quotes/new"} className={({ isActive }) => cn("flex min-h-9 items-center gap-2.5 rounded-lg px-3 text-sm font-medium transition-colors duration-150", isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground")}><Icon size={17} aria-hidden="true" />{label}</NavLink>
              return closeOnNavigate ? <SheetClose asChild key={to}>{link}</SheetClose> : <div key={to}>{link}</div>
            })}
          </div>
        </div>
      ))}
    </nav>
  )
}

function AccountMenu({ name, username, logout, onChangePassword }: { name?: string; username?: string; logout: () => void; onChangePassword: () => void }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild><Button variant="ghost" size="sm" className="max-w-44 gap-1.5 px-2.5"><UserCircle size={18} aria-hidden="true" /><span className="truncate">{name ?? "Account"}</span></Button></DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>{username ?? "Signed in"}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onChangePassword} className="gap-2"><Key size={16} /> Change password</DropdownMenuItem>
        <DropdownMenuItem onClick={logout} className="gap-2"><SignOut size={16} /> Log out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function OpsShell() {
  const { opsUser, logout } = useOpsAuth()
  const [changePasswordOpen, setChangePasswordOpen] = useState(false)

  return (
    <div className="min-h-dvh bg-background lg:flex">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card px-3 py-5 lg:flex" aria-label="Operations sidebar">
        <NavLink to="/overview" className="mb-6 flex items-center gap-2 px-3 font-heading text-base font-semibold text-foreground"><Truck size={22} weight="fill" className="text-accent-foreground" aria-hidden="true" />Raaziq</NavLink>
        <Button asChild className="mb-7 w-full justify-start gap-2 px-3"><NavLink to="/quotes/new"><Plus size={17} /> New Quote</NavLink></Button>
        <SidebarNav />
        <div className="mt-auto space-y-3 border-t border-border pt-4">
          <a href="/track" target="_blank" rel="noreferrer" className="flex min-h-9 items-center gap-2.5 rounded-lg px-3 text-sm font-medium text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground"><MagnifyingGlass size={17} aria-hidden="true" /> Customer Tracking <span aria-hidden="true">↗</span></a>
          <div className="flex items-center justify-between px-2"><span className="text-xs text-muted-foreground">Theme</span><ThemeToggle /></div>
          <AccountMenu name={opsUser?.name} username={opsUser?.username} logout={logout} onChangePassword={() => setChangePasswordOpen(true)} />
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-border bg-background/95 px-4 backdrop-blur-sm lg:px-7">
          <Sheet>
            <SheetTrigger asChild><Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open operations navigation"><List size={21} /></Button></SheetTrigger>
            <SheetContent side="left" className="w-[min(86vw,20rem)] p-0" aria-describedby="mobile-nav-description">
              <SheetHeader className="border-b border-border px-5 py-5"><SheetTitle className="flex items-center gap-2"><Truck size={20} weight="fill" className="text-accent-foreground" /> Raaziq</SheetTitle><SheetDescription id="mobile-nav-description">Operations navigation</SheetDescription></SheetHeader>
              <div className="overflow-y-auto px-3 py-5">
                <Button asChild className="mb-7 w-full justify-start gap-2 px-3"><SheetClose asChild><NavLink to="/quotes/new"><Plus size={17} /> New Quote</NavLink></SheetClose></Button>
                <SidebarNav closeOnNavigate />
                <div className="mt-7 border-t border-border pt-4"><SheetClose asChild><a href="/track" target="_blank" rel="noreferrer" className="flex min-h-10 items-center gap-2.5 rounded-lg px-3 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground"><MagnifyingGlass size={17} /> Customer Tracking ↗</a></SheetClose></div>
              </div>
            </SheetContent>
          </Sheet>
          <NavLink to="/overview" className="flex items-center gap-2 font-heading font-semibold lg:hidden"><Truck size={19} weight="fill" className="text-accent-foreground" /> Raaziq</NavLink>
          <div className="hidden items-center gap-2 text-sm text-muted-foreground lg:flex"><MagnifyingGlass size={16} /><span>Operations workspace</span></div>
          <div className="ml-auto flex items-center gap-1"><a href="/track" target="_blank" rel="noreferrer" aria-label="Customer tracking" className="hidden rounded-lg px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground sm:flex sm:items-center sm:gap-1.5"><MagnifyingGlass size={16} /> Tracking ↗</a><ThemeToggle /><div className="lg:hidden"><AccountMenu name={opsUser?.name} username={opsUser?.username} logout={logout} onChangePassword={() => setChangePasswordOpen(true)} /></div></div>
        </header>
        <main className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 sm:py-8 lg:px-7"><Outlet /></main>
      </div>
      <ChangePasswordDialog open={changePasswordOpen} onOpenChange={setChangePasswordOpen} />
    </div>
  )
}
