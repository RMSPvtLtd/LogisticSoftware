import { useMemo } from "react"
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"

export interface CommandItemData {
  id: string
  label: string
  hint?: string
  group: string
  onSelect: () => void
}

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (v: boolean) => void
  items: CommandItemData[]
  placeholder?: string
}

// Generic cmdk-based palette shell. Client-side substring filter only --
// every portal-specific palette (Ops/Worker/Customer) supplies `items` from
// data it already fetched within its own authorization boundary; this
// component makes no network calls itself.
export function CommandPalette({ open, onOpenChange, items, placeholder = "Search…" }: CommandPaletteProps) {
  const groups = useMemo(() => {
    const byGroup = new Map<string, CommandItemData[]>()
    for (const item of items) {
      const list = byGroup.get(item.group) ?? []
      list.push(item)
      byGroup.set(item.group, list)
    }
    return Array.from(byGroup.entries())
  }, [items])

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title="Raaziq search">
      <Command shouldFilter>
        <CommandInput placeholder={placeholder} />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          {groups.map(([group, groupItems]) => (
            <CommandGroup key={group} heading={group}>
              {groupItems.map((item) => (
                <CommandItem
                  key={item.id}
                  value={`${item.label} ${item.hint ?? ""}`}
                  onSelect={() => {
                    item.onSelect()
                    onOpenChange(false)
                  }}
                >
                  <div className="flex min-w-0 flex-1 items-baseline justify-between gap-2">
                    <span className="truncate">{item.label}</span>
                    {item.hint && <span className="shrink-0 text-xs text-muted-foreground">{item.hint}</span>}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          ))}
        </CommandList>
      </Command>
    </CommandDialog>
  )
}
