# Raaziq MVP — Freight Quotation Automation + Shipment Tracking

Backend for the Raaziq MVP: a Pakistan-based freight forwarder's two core workflows —
freight quotation automation, and shipment tracking across the forwarding lifecycle.

This is the backend only (Phases 1–4). There is no frontend yet; the API below is what
a future React app will consume.

## Stack

Python, FastAPI, SQLAlchemy 2.x (ORM), Alembic, Pydantic, PostgreSQL (production),
SQLite (tests — no PostgreSQL or Docker required to run the test suite), pytest, uv.

## Project layout

```
backend/
├── app/
│   ├── main.py            FastAPI app, router mounting, centralized error handlers
│   ├── config.py          every tunable business value (markup %, validity days, ...)
│   ├── db.py               engine, session factory, get_db dependency
│   ├── errors.py           domain exceptions -> HTTP status mapping
│   ├── dependencies.py     current_actor (no auth yet; isolated for later)
│   ├── models/              SQLAlchemy models + the sole owner of stage ordering (enums.py)
│   ├── schemas/             Pydantic request/response models
│   ├── services/            business logic: pricing, quotes, transitions, tracking
│   ├── adapters/             TrackingAdapter protocol + MockTrackingAdapter
│   └── api/                  FastAPI routers
├── alembic/versions/         one initial migration
├── seeds/seed.py              idempotent demo data
└── tests/                     pytest suite (SQLite, no external DB needed)
```

## Local setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync --extra dev
cp .env.example .env   # adjust DATABASE_URL etc. as needed
```

### Environment variables

See `backend/.env.example` for the full list with defaults:

- `DATABASE_URL` — PostgreSQL connection string in production.
- `DEFAULT_MARKUP_PERCENT`, `QUOTE_VALIDITY_DAYS` — pricing/quoting tunables.
- `VOLUMETRIC_FACTOR_AIR` / `_SEA` / `_ROAD` — kg-per-CBM dimensional weight factors.
- `JOB_NUMBER_PREFIX`, `JOB_NUMBER_PADDING` — job number format, e.g. `RAZ-2026-00001`.
- `CORS_ORIGINS`, `DEFAULT_ACTOR`.

`.env` is never committed (see `.gitignore`).

### Database migration

Requires a running PostgreSQL instance reachable at `DATABASE_URL`:

```bash
uv run alembic upgrade head
```

### Seed data

Idempotent — safe to run more than once. Seeds three trade lanes (Lahore→Dubai air,
Karachi→Jebel Ali sea, Lahore→Karachi road), three customers, and three inquiries carried
to different points in the workflow (a draft quote, an accepted shipment in transit, and
an accepted shipment marked at risk):

```bash
uv run python -m seeds.seed
```

### Run the server

```bash
uv run uvicorn app.main:app --reload
```

### Run the tests

The test suite runs entirely on a throwaway in-memory SQLite database — no PostgreSQL or
Docker needed:

```bash
uv run pytest -q
```

## API overview

```
POST/GET  /customers · /customers/{id}
POST/GET  /inquiries · /inquiries/{id}

POST      /quotes/generate
GET       /quotes · /quotes/{id}
PATCH     /quotes/{id}/line-items      manual override (draft only)
POST      /quotes/{id}/send            marks sent only — no email/PDF in this MVP
POST      /quotes/{id}/accept          transactional, idempotent; creates the Shipment

GET       /shipments                   filters: stage, at_risk, mode
GET       /shipments/{id}
POST      /shipments/{id}/status               next-stage-only progression
POST      /shipments/{id}/status/correct       repair path, any operational stage, requires a reason
POST      /shipments/{id}/references
POST      /shipments/{id}/risk

GET       /tracking/{reference}        public, customer-safe (job number or any reference)
GET       /meta/stages                 canonical ordered stages + human-readable labels
```

Full request/response shapes are in `app/schemas/`; interactive docs are available at
`/docs` once the server is running.

### The quote → shipment seam

Accepting a quote (`POST /quotes/{id}/accept`) is the one place the two workflows meet.
It is transactional and idempotent: accepting the same quote twice returns the same
shipment rather than creating a second one, and if anything fails partway through — job
number allocation, shipment creation, the initial status event — the entire operation
(including the job number counter increment) rolls back together. A failed acceptance
attempt never permanently consumes a job number sequence value.

### Shipment stages

Fixed, ordered enum: `job_opened → docs_filed → picked_up → in_transit →
customs_clearance → arrived → delivered`. `POST /shipments/{id}/status` only accepts the
immediate next stage — no skipping ahead, no going backwards. If an operational mistake
needs correcting, `POST /shipments/{id}/status/correct` can move a shipment to any
operational stage, but requires a reason and always adds a new event; it never edits or
deletes history. `StatusEvent` rows are append-only everywhere — there is no endpoint that
updates or deletes one.

### At-risk shipments

`is_at_risk` / `risk_reason` are independent of stage — there is no `delayed` stage.
`risk_reason` is internal-only and is never returned by the customer tracking endpoint,
only the `at_risk` boolean is.

## Tracking adapter architecture

Raaziq does not integrate a real tracking provider (ShipsGo, a carrier API, WeBOC, PSW,
...) in this MVP. Instead, there's a small interface that a future integration plugs
into without touching the shipment/status data model:

```
Carrier / Tracking Provider
        ↓
TrackingAdapter.get_status(reference) -> NormalizedStatus | None
        ↓
services.tracking.ingest_adapter_update()
        ↓  (goes through the same rules as a manual update)
services.transitions.advance_stage()
        ↓
StatusEvent (source=automated)
        ↓
Shipment.stage
        ↓
Ops dashboard + customer tracking
```

`app/adapters/tracking.py` defines the `TrackingAdapter` protocol and the
`NormalizedStatus` shape it returns — provider-specific status codes are normalized into
Raaziq's own `ShipmentStage` at this boundary and never leak further into the
application. `app/adapters/mock.py` provides `MockTrackingAdapter`, a fake adapter with
canned responses, for local development and tests.

Ingestion never writes to `Shipment.stage` or `StatusEvent` directly — it always goes
through `services.transitions.advance_stage`, the same function a manual status update
uses. If a provider reports an invalid or backwards stage, nothing is mutated; the update
is treated as an ingestion failure (`TrackingIngestionFailed`), not silently applied or
used to bypass the transition rules.

A future real adapter looks conceptually like:

```python
class ShipsGoAdapter(TrackingAdapter):
    def get_status(self, reference: str) -> NormalizedStatus | None:
        # call the provider, normalize its status into ShipmentStage
        ...
```

No ETA prediction, GPS/IoT tracking, or live WeBOC/PSW integration is implemented —
customs updates are entered manually by ops for this MVP, through the same status-update
path as any other stage change.

## What's out of scope for this MVP

React frontend (a follow-up), authentication/RBAC, predictive ETA, AI pricing or
shipment prediction, GPS/IoT, live WeBOC/PSW integration, ShipsGo/carrier API
integration, multi-carrier RFQ automation, live spot-rate feeds, accounting/ERP,
invoicing, payments, microservices, event buses, Redis, Celery, Kubernetes.
