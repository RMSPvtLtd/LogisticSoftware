# Docs

Cross-vertical documentation. Vertical-specific documentation (how the air backend's stage
pipeline works, its API surface, etc.) stays close to the code in `air/README.md` /
`sea/README.md` rather than here — this folder is for things that span or precede both
verticals.

- `architecture/` — system-level diagrams and decisions (how air/sea/shared relate, what's
  actually shared vs. duplicated on purpose).
- `api/` — cross-vertical API conventions, if/when air and sea need to agree on one (auth
  scheme, error shape, versioning).
- `database/` — cross-vertical data conventions.
- `deployment/` — how the monorepo as a whole gets deployed (one service per vertical? a
  shared gateway?) — not yet decided, hence empty.
- `product/` — product requirements/specs that aren't code.
