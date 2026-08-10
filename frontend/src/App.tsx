import { Navigate, Route, Routes } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { StagesProvider } from "@/hooks/useStages"
import { OpsShell } from "@/components/layout/OpsShell"
import { PublicShell } from "@/components/layout/PublicShell"
import { ShipmentListPage } from "@/pages/ShipmentListPage"
import { ShipmentDetailPage } from "@/pages/ShipmentDetailPage"
import { QuoteFlowPage } from "@/pages/QuoteFlowPage"
import { TrackingPage } from "@/pages/TrackingPage"

function App() {
  return (
    <StagesProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/shipments" replace />} />

        <Route element={<OpsShell />}>
          <Route path="/shipments" element={<ShipmentListPage />} />
          <Route path="/shipments/:id" element={<ShipmentDetailPage />} />
          <Route path="/quotes/new" element={<QuoteFlowPage />} />
          <Route path="/quotes/:id" element={<QuoteFlowPage />} />
        </Route>

        <Route element={<PublicShell />}>
          <Route path="/track" element={<TrackingPage />} />
          <Route path="/track/:reference" element={<TrackingPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/shipments" replace />} />
      </Routes>
      <Toaster position="top-right" richColors />
    </StagesProvider>
  )
}

export default App
