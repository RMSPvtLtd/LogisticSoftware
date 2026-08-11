# LogisticSoftware

Two independent freight-forwarding verticals, developed in parallel and merged into one
repository — see [`sea-and-air/`](sea-and-air).

- **[air/](sea-and-air/air)** — Raaziq, the air-freight forwarder MVP (built; see its
  [README](sea-and-air/air/README.md) for setup, architecture, and demo credentials).
- **[sea/](sea-and-air/sea)** — the sea-freight vertical (not started yet).
- **[shared/](sea-and-air/shared)** — code promoted here once genuinely duplicated between
  the two.

Each vertical is a self-contained project (its own backend, frontend, migrations) — you
shouldn't need anything outside `air/` to build or run it, and the same will hold for
`sea/`. See [`sea-and-air/README.md`](sea-and-air/README.md) for the full layout and how
the two verticals are meant to merge.
