import { Navigate, Route, Routes, useNavigate } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { StagesProvider } from "@/hooks/useStages"
import { WorkerAuthProvider, useWorkerAuth } from "@/hooks/useWorkerAuth"
import { CustomerAuthProvider, useCustomerAuth } from "@/hooks/useCustomerAuth"
import { AppShell } from "@/components/layout/AppShell"
import { OPS_NAV, CUSTOMER_NAV, WORKER_NAV } from "@/components/layout/nav-config"
import { OpsCommandPalette } from "@/components/command/OpsCommandPalette"
import { WorkerCommandPalette } from "@/components/command/WorkerCommandPalette"
import { CustomerCommandPalette } from "@/components/command/CustomerCommandPalette"
import { PublicShell } from "@/components/layout/PublicShell"
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
import { DashboardPage } from "@/pages/DashboardPage"
import { LoaderPreviewPage } from "@/pages/LoaderPreviewPage"

// Ops has no login in this MVP -- no identity/logout to pass to AppShell.
function OpsAppShell() {
  return <AppShell brandHref="/" navItems={OPS_NAV} commandPalette={(ctx) => <OpsCommandPalette {...ctx} />} />
}

function WorkerAppShell() {
  const { worker, logout } = useWorkerAuth()
  const navigate = useNavigate()
  return (
    <AppShell
      brandHref="/worker/queue"
      navItems={WORKER_NAV}
      identityLabel={worker?.name}
      onLogout={() => {
        logout()
        navigate("/worker/login")
      }}
      commandPalette={(ctx) => <WorkerCommandPalette {...ctx} />}
    />
  )
}

function CustomerAppShell() {
  const { customer, logout } = useCustomerAuth()
  const navigate = useNavigate()
  return (
    <AppShell
      brandHref="/customer/shipments"
      navItems={CUSTOMER_NAV}
      identityLabel={customer?.name}
      onLogout={() => {
        logout()
        navigate("/customer/login")
      }}
      commandPalette={(ctx) => <CustomerCommandPalette {...ctx} />}
    />
  )
}

function App() {
  return (
    <StagesProvider>
      <Routes>
        <Route element={<OpsAppShell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/shipments" element={<ShipmentListPage />} />
          <Route path="/shipments/:id" element={<ShipmentDetailPage />} />
          <Route path="/quotes/new" element={<QuoteFlowPage />} />
          <Route path="/quotes/:id" element={<QuoteFlowPage />} />
          <Route path="/workers" element={<WorkersAdminPage />} />
          <Route path="/customers" element={<CustomersAdminPage />} />
        </Route>

        <Route element={<PublicShell />}>
          {/* Same showcase on both paths: /loading is the dev shorthand,
              /landing is the one shared from the deployed site. */}
          <Route path="/loading" element={<LoaderPreviewPage />} />
          <Route path="/landing" element={<LoaderPreviewPage />} />
          <Route path="/track" element={<TrackingPage />} />
          <Route path="/track/sea" element={<TrackingPage />} />
          <Route path="/track/sea/:containerNumber" element={<TrackingPage />} />
          <Route path="/track/:reference" element={<TrackingPage />} />
        </Route>

        <Route
          path="/worker/*"
          element={
            <WorkerAuthProvider>
              <Routes>
                <Route path="login" element={<WorkerLoginPage />} />
                <Route
                  element={
                    <ProtectedWorkerRoute>
                      <WorkerAppShell />
                    </ProtectedWorkerRoute>
                  }
                >
                  <Route path="queue" element={<WorkerQueuePage />} />
                </Route>
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
                      <CustomerAppShell />
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
