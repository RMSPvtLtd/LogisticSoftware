import { useRef, useState } from "react"
import { toast } from "sonner"
import { DownloadSimple, FilePdf, UploadSimple } from "@phosphor-icons/react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { StageBadge } from "@/components/shared/StageBadge"
import { useAsync } from "@/hooks/useAsync"
import { documentsApi, downloadAuthedFile, ApiError } from "@/lib/api/client"
import { formatDateTime } from "@/lib/format"
import type { DocumentType } from "@/lib/api/types"

const MAX_UPLOAD_BYTES = 4 * 1024 * 1024

const DOCUMENT_TYPE_LABEL: Record<DocumentType, string> = {
  quotation: "Quotation",
  invoice: "Invoice",
  airway_bill: "Airway Bill",
  gd: "GD",
  customs: "Customs",
  shipment_receipt: "Shipment Receipt",
  examination: "Examination",
  delivery: "Delivery",
  other: "Other",
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Optional at every stage -- ops can attach any PDF (airway bill scan,
// customs paperwork, ...) whenever, tagged with whatever stage the
// shipment is currently at. Stored in Postgres (see backend/services/
// documents.py); not embedded in ShipmentRead, so this fetches its own list.
export function DocumentsCard({ shipmentId }: { shipmentId: number }) {
  const documents = useAsync(() => documentsApi.list(shipmentId), [shipmentId])
  const [documentType, setDocumentType] = useState<DocumentType>("other")
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFileChosen(file: File | undefined) {
    if (!file) return
    if (file.type !== "application/pdf") {
      toast.error("Only PDF files can be attached.")
      return
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      toast.error(`File exceeds the ${MAX_UPLOAD_BYTES / (1024 * 1024)} MB upload limit.`)
      return
    }
    setUploading(true)
    try {
      await documentsApi.upload(shipmentId, file, documentType)
      toast.success("Document uploaded")
      documents.reload()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not upload document.")
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ""
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Documents</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {documents.data && documents.data.length > 0 ? (
          <ul className="space-y-1.5 text-sm">
            {documents.data.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between gap-2 rounded-lg bg-muted px-3 py-2">
                <div className="flex min-w-0 items-center gap-2">
                  <FilePdf size={18} className="shrink-0 text-muted-foreground" />
                  <div className="min-w-0">
                    <p className="truncate font-medium">{doc.filename}</p>
                    <p className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
                      <StageBadge stage={doc.stage} className="px-1.5 py-0.5" />
                      <Badge variant="outline" className="px-1.5 py-0.5 text-[10px]">
                        {DOCUMENT_TYPE_LABEL[doc.document_type]}
                      </Badge>
                      {formatBytes(doc.size_bytes)} · {formatDateTime(doc.created_at)}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    downloadAuthedFile(documentsApi.downloadUrl(doc.id), doc.filename).catch(() =>
                      toast.error("Could not download document."),
                    )
                  }
                  className="shrink-0 rounded p-1.5 text-muted-foreground outline-none hover:bg-background hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label={`Download ${doc.filename}`}
                >
                  <DownloadSimple size={16} />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No documents attached yet.</p>
        )}
        <Separator />
        <div className="flex gap-2">
          <Select value={documentType} onValueChange={(v) => setDocumentType(v as DocumentType)}>
            <SelectTrigger className="w-full" aria-label="Document type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(DOCUMENT_TYPE_LABEL) as DocumentType[]).map((t) => (
                <SelectItem key={t} value={t}>
                  {DOCUMENT_TYPE_LABEL[t]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => handleFileChosen(e.target.files?.[0])}
        />
        <Button
          variant="outline"
          size="sm"
          className="w-full gap-1.5"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          <UploadSimple size={16} />
          {uploading ? "Uploading…" : "Attach PDF"}
        </Button>
      </CardContent>
    </Card>
  )
}
