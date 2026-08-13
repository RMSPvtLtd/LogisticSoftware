import { useEffect } from "react"

// Global Cmd/Ctrl+K listener. Toggles rather than only-opens so the same
// shortcut closes the palette too.
export function useCommandPaletteShortcut(toggle: () => void) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        toggle()
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [toggle])
}
