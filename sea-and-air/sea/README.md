# Sea Freight Vertical

Not built yet. This mirrors the directory layout of [`../air`](../air) exactly (frontend,
backend, ai, database, integrations, tests) so the sea and air verticals stay structurally
consistent and easy to merge/compare, but every folder here is currently an empty
placeholder (`.gitkeep`).

To start building: treat this directory the same way `air/` is set up — a self-contained
FastAPI backend (`backend/`) with its own `pyproject.toml`/`alembic.ini` at this directory's
root, and a self-contained Vite/React frontend (`frontend/`). `air/pyproject.toml` and
`air/backend/` are a reasonable starting template to copy from and adapt (sea-freight has
different domain concepts — container/vessel tracking, port calls, bills of lading — so
expect the models/schemas/services layer to diverge quickly from air's).

See [`../air/README.md`](../air/README.md) for the fuller write-up of conventions this
project follows (stage-based tracking, worker/customer portals, migration patterns, etc.)
that are worth reusing here where the domain overlaps.
