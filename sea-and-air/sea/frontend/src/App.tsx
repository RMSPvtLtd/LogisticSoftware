import { Navigate, Route, Routes } from "react-router-dom"
import { SeaShell } from "@/components/layout/SeaShell"
import { SeaTrackerPage } from "@/pages/SeaTrackerPage"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/track" replace />} />
      <Route element={<SeaShell />}>
        <Route path="/track" element={<SeaTrackerPage />} />
        <Route path="/track/:containerNumber" element={<SeaTrackerPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/track" replace />} />
    </Routes>
  )
}

export default App
