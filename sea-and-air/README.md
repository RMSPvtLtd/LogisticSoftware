# sea-and-air

Two independent freight-forwarding verticals — **air** (built, see [`air/`](air)) and
**sea** (not started, see [`sea/`](sea)) — developed in parallel by separate people and
merged here rather than as two separate repos, so shared pieces can be promoted into
[`shared/`](shared) once they actually duplicate.

## Layout

```
sea-and-air/
├── air/            Air freight vertical — frontend, backend, ai, database, integrations, tests
├── sea/            Sea freight vertical — same shape as air/, currently empty scaffolding
├── shared/         Code/types promoted here once genuinely duplicated between air and sea
├── docs/           Cross-vertical documentation
├── infrastructure/ Deployment/environment config, per environment tier
└── scripts/        Cross-vertical operational scripts
```

`.github/` (CI workflows, PR templates) lives at the **repository root**, not inside
`sea-and-air/` — GitHub only reads workflow files from `<repo-root>/.github/workflows/`,
so nesting it here would make it silently do nothing.

## Working on air or sea

Each vertical is meant to be a self-contained project — its own `pyproject.toml` /
`uv.lock` for the backend, its own `package.json` for the frontend, its own migrations and
seed data. You shouldn't need anything from the other vertical to build or run yours. See
[`air/README.md`](air/README.md) for the fully worked example (setup, conventions, API
overview) — `sea/` follows the same shape once someone starts building it.

## Merging air and sea

Because each vertical only touches its own folder, air and sea development can happen on
separate branches with no file overlap (barring `shared/`) — merging is a non-conflicting
directory union, not a line-by-line reconciliation. Only promote something into `shared/`
once both verticals actually have it and keeping two copies in sync would be worse than
the coupling of sharing it.
