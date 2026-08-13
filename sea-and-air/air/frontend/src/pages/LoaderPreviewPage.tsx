import { RaaziqLoader } from "@/components/shared/RaaziqLoader"

// Standalone preview of the RaaziqLoader variants -- not linked from any
// nav, just a direct URL (/loading) to inspect the animation in isolation.
export function LoaderPreviewPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-10 px-4 py-16">
      <div className="text-center">
        <h1 className="font-heading text-2xl font-semibold text-foreground">RaaziqLoader</h1>
        <p className="mt-1 text-sm text-muted-foreground">Truck stays put; road markers conveyor past underneath.</p>
      </div>

      <Section title="full — page/section loading">
        <RaaziqLoader variant="full" label="Loading dashboard…" />
      </Section>

      <Section title="inline — compact, next to a button">
        <RaaziqLoader variant="inline" label="Generating quote…" />
      </Section>

      <Section title="progress — tied to real shipment stage (25%)">
        <RaaziqLoader variant="progress" progress={0.25} />
      </Section>

      <Section title="progress — 60%">
        <RaaziqLoader variant="progress" progress={0.6} />
      </Section>

      <Section title="progress — 100%">
        <RaaziqLoader variant="progress" progress={1} />
      </Section>

      <Section title="plane — air search">
        <RaaziqLoader variant="inline" vehicle="plane" label="Fetching shipment information…" />
      </Section>

      <Section title="ship — sea search">
        <RaaziqLoader variant="inline" vehicle="ship" label="Fetching shipment information…" />
      </Section>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card py-8">
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{title}</p>
      {children}
    </div>
  )
}
