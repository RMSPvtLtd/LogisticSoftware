import { RaaziqLoader } from "@/components/shared/RaaziqLoader"

// Showcase of every RaaziqLoader variant, served at /loading. Not linked
// from any nav -- direct URL only.
export function LoaderPreviewPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-8 px-4 py-16">
      <div className="text-center">
        <h1 className="font-heading text-2xl font-semibold text-foreground">Raaziq loading animations</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          One loader per freight mode. The vehicle holds position and the world moves past it, which is what
          reads as travel without the loop ever jumping.
        </p>
      </div>

      <Group title="Air" />
      <Section title="Air search — clouds drift back, speed lines stream past">
        <RaaziqLoader variant="full" vehicle="plane" label="Fetching shipment information…" />
      </Section>
      <Section title="Air — compact, inline with a panel">
        <RaaziqLoader variant="inline" vehicle="plane" label="Fetching shipment information…" />
      </Section>

      <Group title="Sea" />
      <Section title="Sea search — the vessel bobs, the swell travels">
        <RaaziqLoader variant="full" vehicle="ship" label="Fetching shipment information…" />
      </Section>
      <Section title="Sea — compact, inline with a panel">
        <RaaziqLoader variant="inline" vehicle="ship" label="Fetching shipment information…" />
      </Section>

      <Group title="Road / default" />
      <Section title="Page or section loading">
        <RaaziqLoader variant="full" label="Loading dashboard…" />
      </Section>
      <Section title="Compact, next to a button">
        <RaaziqLoader variant="inline" label="Generating quote…" />
      </Section>

      <Group title="Progress — driven by a shipment's real stage" />
      <Section title="25%">
        <RaaziqLoader variant="progress" progress={0.25} />
      </Section>
      <Section title="60%">
        <RaaziqLoader variant="progress" progress={0.6} />
      </Section>
      <Section title="100%">
        <RaaziqLoader variant="progress" progress={1} />
      </Section>
    </div>
  )
}

function Group({ title }: { title: string }) {
  return (
    <h2 className="mt-4 border-b border-border pb-2 font-heading text-sm font-semibold text-foreground">
      {title}
    </h2>
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
