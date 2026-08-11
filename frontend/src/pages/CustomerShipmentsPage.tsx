import { useState } from "react"
import { Link } from "react-router-dom"
import { Package } from "@phosphor-icons/react"
import { PageHeader } from "@/components/shared/PageHeader"
import { StageBadge } from "@/components/shared/StageBadge"
import { RiskBadge } from "@/components/shared/RiskBadge"
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAsync } from "@/hooks/useAsync"
import { useCustomerAuth } from "@/hooks/useCustomerAuth"
import { customerPortalApi } from "@/lib/api/client"
import { formatDateTime } from "@/lib/format"

type Tab = "active" | "completed"

export function CustomerShipmentsPage() {
  const { token } = useCustomerAuth()
  const [tab, setTab] = useState<Tab>("active")

  const shipments = useAsync(
    () => customerPortalApi.shipments(token!, tab === "completed"),
    [token, tab],
  )

  return (
    <div>
      <PageHeader title="Shipments" description="Every job we're moving for you, past and present." />

      <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)} className="mb-4">
        <TabsList>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
        </TabsList>
      </Tabs>

      {shipments.loading && <LoadingState rows={5} />}
      {!shipments.loading && shipments.error && <ErrorState message={shipments.error} onRetry={shipments.reload} />}
      {!shipments.loading && !shipments.error && (shipments.data?.length ?? 0) === 0 && (
        <EmptyState
          icon={<Package size={32} />}
          title={tab === "completed" ? "No completed shipments yet" : "No active shipments"}
          description={
            tab === "completed"
              ? "Shipments appear here once they've been invoiced."
              : "New shipments will show up here as soon as they're created."
          }
        />
      )}
      {!shipments.loading && !shipments.error && (shipments.data?.length ?? 0) > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job Number</TableHead>
                <TableHead>Route</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>Last Updated</TableHead>
                <TableHead>Risk</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {shipments.data!.map((shipment) => (
                <TableRow key={shipment.id}>
                  <TableCell className="font-medium tabular-nums">
                    <Link
                      to={`/customer/shipments/${shipment.id}`}
                      className="rounded outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      {shipment.job_number ?? `Inquiry #${shipment.id}`}
                    </Link>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {shipment.origin} → {shipment.destination}
                  </TableCell>
                  <TableCell>
                    <StageBadge stage={shipment.stage} />
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground tabular-nums">
                    {formatDateTime(shipment.updated_at)}
                  </TableCell>
                  <TableCell>{shipment.is_at_risk && <RiskBadge />}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
