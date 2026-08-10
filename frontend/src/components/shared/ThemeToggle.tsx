import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { Moon, Sun } from "@phosphor-icons/react"
import { Button } from "@/components/ui/button"

// Avoids a hydration/flash mismatch: next-themes only knows the resolved
// theme after mount (it reads localStorage/matchMedia client-side).
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  if (!mounted) return <div className="size-9" aria-hidden="true" />

  const isDark = resolvedTheme === "dark"

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}
    </Button>
  )
}
