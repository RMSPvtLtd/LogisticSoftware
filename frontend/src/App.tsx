import { Navigate, Route, Routes } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { StagesProvider } from "@/hooks/useStages"
import { WorkerAuthProvider } from "@/hooks/useWorkerAuth"
import { CustomerAuthProvider } from "@/hooks/useCustomerAuth"
import { OpsShell } from "@/components/layout/OpsShell"
import { PublicShell } from "@/components/layout/PublicShell"
import { CustomerShell } from "@/components/layout/CustomerShell"
import { ProtectedWorkerRoute } from "@/components/shared/ProtectedWorkerRoute"
import { ProtectedCustomerRoute } from "@/components/shared/ProtectedCustomerRoute"
import { ShipmentListPage } from "@/pages/ShipmentListPage"
import { ShipmentDetailPage } from "@/pages/ShipmentDetailPage"
import { QuoteFlowPage } from "@/pages/QuoteFlowPage"
import { TrackingPage } from "@/pages/TrackingPage"
import { WorkerLoginPage } from "@/pages/WorkerLoginPage"
import { WorkerQueuePage } from "@/pages/WorkerQueuePage"
import { WorkersAdminPage } from "@/pages/WorkersAdminPage"
import { CustomersAdminPage } from "@/pages/CustomersAdminPage"
import { CustomerLoginPage } from "@/pages/CustomerLoginPage"
import { CustomerShipmentsPage } from "@/pages/CustomerShipmentsPage"
import { CustomerShipmentDetailPage } from "@/pages/CustomerShipmentDetailPage"
import { CustomerQuotesPage } from "@/pages/CustomerQuotesPage"
import { CustomerQuoteDetailPage } from "@/pages/CustomerQuoteDetailPage"

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
          <Route path="/workers" element={<WorkersAdminPage />} />
          <Route path="/customers" element={<CustomersAdminPage />} />
        </Route>

        <Route element={<PublicShell />}>
          <Route path="/track" element={<TrackingPage />} />
          <Route path="/track/:reference" element={<TrackingPage />} />
        </Route>

        <Route
          path="/worker/*"
          element={
            <WorkerAuthProvider>
              <Routes>
                <Route path="login" element={<WorkerLoginPage />} />
                <Route
                  path="queue"
                  element={
                    <ProtectedWorkerRoute>
                      <WorkerQueuePage />
                    </ProtectedWorkerRoute>
                  }
                />
                <Route path="*" element={<Navigate to="/worker/login" replace />} />
              </Routes>
            </WorkerAuthProvider>
          }
        />

        <Route
          path="/customer/*"
          element={
            <CustomerAuthProvider>
              <Routes>
                <Route path="login" element={<CustomerLoginPage />} />
                <Route
                  element={
                    <ProtectedCustomerRoute>
                      <CustomerShell />
                    </ProtectedCustomerRoute>
                  }
                >
                  <Route path="shipments" element={<CustomerShipmentsPage />} />
                  <Route path="shipments/:id" element={<CustomerShipmentDetailPage />} />
                  <Route path="quotes" element={<CustomerQuotesPage />} />
                  <Route path="quotes/:id" element={<CustomerQuoteDetailPage />} />
                </Route>
                <Route path="*" element={<Navigate to="/customer/login" replace />} />
              </Routes>
            </CustomerAuthProvider>
          }
        />

        <Route path="*" element={<Navigate to="/shipments" replace />} />
      </Routes>
      <Toaster position="top-right" richColors />
    </StagesProvider>
  )
}

export default App
