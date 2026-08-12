# sea-and-air

Two independent freight-forwarding verticals — **air** (see [`air/`](air), the full
quotation + shipment pipeline) and **sea** (see [`sea/`](sea), a container tracker so far)
— developed in parallel by separate people and merged here rather than as two separate
repos, so shared pieces can be promoted into [`shared/`](shared) once they actually
duplicate.

## Layout

```
sea-and-air/
├── air/            Air freight vertical — frontend, backend, ai, database, integrations, tests
├── sea/            Sea freight vertical — backend only (container tracker's UI is a Sea
│                    mode inside air's frontend, not a second frontend — see below)
├── shared/         Code/types promoted here once genuinely duplicated between air and sea
├── docs/           Cross-vertical documentation
├── infrastructure/ Deployment/environment config, per environment tier
└── scripts/        Cross-vertical operational scripts
```

**One exception to "independent verticals":** the customer-facing tracking page lives once,
in `air/frontend`, with an Air/Sea toggle — not as two separate sites. Air's dev server
proxies sea-tracking requests to sea's backend server-side (`air/frontend/vite.config.ts`'s
`/sea-api` rule), so the browser only ever talks to one origin. Backends stay fully
independent either way — see [`air/README.md`](air/README.md#pages) and
[`sea/README.md`](sea/README.md) for how that split works.

`.github/` (CI workflows, PR templates) lives at the **repository root**, not inside
`sea-and-air/` — GitHub only reads workflow files from `<repo-root>/.github/workflows/`,
so nesting it here would make it silently do nothing.

## Working on air or sea

Each vertical's *backend* is a fully self-contained project — its own `pyproject.toml` /
`uv.lock`, its own migrations and seed data (or, for sea's tracker so far, no database at
all — see [`sea/README.md`](sea/README.md#no-persistence-on-purpose)). The frontend is the
one shared surface (see above) — building/running sea's backend needs nothing from air,
but exercising the Sea toggle in the browser needs air's frontend running too. See
[`air/README.md`](air/README.md) and [`sea/README.md`](sea/README.md) for the fully worked
examples (setup, conventions, API overview).

## Merging air and sea

Backend development can happen on separate branches with no file overlap, same as before —
`air/backend/` and `sea/backend/` never touch the same file. The frontend is the one place
that isn't true: adding a sea feature to the tracking toggle means touching files under
`air/frontend/`, so that slice needs the normal review/merge discipline a shared file
would, rather than being a conflict-free directory union like the rest of the split. Only
promote something into `shared/` once both verticals actually have it and keeping two
copies in sync would be worse than the coupling of sharing it.
