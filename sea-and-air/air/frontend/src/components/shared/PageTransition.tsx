import { useLocation } from "react-router-dom"

// Applies a subtle fade-up on every route change. Mounted once inside
// AppShell's content area and inside PublicShell -- not per-page
// boilerplate. key={pathname} forces React to remount the wrapper (and
// replay the animation) on navigation.
export function PageTransition({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  return (
    <div key={location.pathname} className="animate-page-in">
      {children}
    </div>
  )
}
