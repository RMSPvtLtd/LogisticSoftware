import { useParams } from "react-router-dom"
import { PageHeader } from "@/components/shared/PageHeader"
import { InquiryForm } from "@/components/quotes/InquiryForm"
import { QuoteBreakdown } from "@/components/quotes/QuoteBreakdown"

export function QuoteFlowPage() {
  const { id } = useParams<{ id: string }>()
  const quoteId = id ? Number(id) : null

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title={quoteId ? "Quote" : "New Quote"}
        description={
          quoteId
            ? "Review the breakdown, adjust pricing if needed, then send or accept."
            : "Enter the inquiry details to generate a priced quote automatically."
        }
      />
      {quoteId ? <QuoteBreakdown quoteId={quoteId} /> : <InquiryForm />}
    </div>
  )
}
