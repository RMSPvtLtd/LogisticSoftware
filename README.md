# Raaziq MVP — Freight Quotation Automation + Shipment Tracking

Raaziq MVP: a Pakistan-based air-freight forwarder's two core workflows — freight
quotation automation, and shipment tracking across the forwarding lifecycle — plus a
worker portal so warehouse/ops staff mark their own stage done instead of a single admin
updating everything. A FastAPI backend and a React frontend with three surfaces: the ops
dashboard, the worker portal, and the public customer tracking page.

## Stack

**Backend:** Python, FastAPI, SQLAlchemy 2.x (ORM), Alembic, Pydantic, PostgreSQL
(production), SQLite (tests — no PostgreSQL or Docker required to run the test suite),
pytest, uv.

**Frontend:** React, TypeScript, Vite, Tailwind CSS v4, shadcn/ui (Radix primitives),
Phosphor icons, React Router.

## Project layout

```
backend/
├── app/
│   ├── main.py            FastAPI app, router mounting, centralized error handlers
│   ├── config.py          every tunable business value (markup %, validity days, ...)
│   ├── db.py               engine, session factory, get_db dependency
│   ├── errors.py           domain exceptions -> HTTP status mapping
│   ├── dependencies.py     current_actor (ops side has no login; isolated for later)
│   ├── security.py         worker auth: password hashing, JWT, get_current_worker
│   ├── models/              SQLAlchemy models + the sole owner of stage ordering (enums.py)
│   ├── schemas/             Pydantic request/response models
│   ├── services/            business logic: pricing, quotes, transitions, tracking, workers
│   ├── adapters/             TrackingAdapter protocol + MockTrackingAdapter
│   └── api/                  FastAPI routers (incl. auth, workers, worker_portal)
├── alembic/versions/         two migrations (initial schema, worker areas)
├── seeds/seed.py              idempotent demo data
└── tests/                     pytest suite (SQLite, no external DB needed)

frontend/
├── src/
│   ├── main.tsx / App.tsx      entry point, ThemeProvider, router
│   ├── index.css                design tokens (colors, fonts) as CSS variables
│   ├── lib/
│   │   ├── api/                 typed fetch client mirroring the backend schemas
│   │   └── format.ts            money/date formatting helpers
│   ├── hooks/                   useStages, useAsync, useWorkerAuth (worker login/session)
│   ├── components/
│   │   ├── ui/                   shadcn/ui primitives
│   │   ├── layout/                OpsShell (staff nav) / PublicShell (tracking page)
│   │   ├── shared/                StageBadge, RiskBadge, StageChecklist, EventTimeline, ...
│   │   └── quotes/                InquiryForm, QuoteBreakdown
│   └── pages/                    ShipmentListPage, ShipmentDetailPage, QuoteFlowPage,
│                                  TrackingPage, WorkersAdminPage, WorkerLoginPage, WorkerQueuePage
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
- `VOLUMETRIC_FACTOR_AIR` / `_SEA` / `_ROAD` — kg-per-CBM dimensional weight factors (sea/road
  are unused in practice — see "Air freight only" below).
- `JOB_NUMBER_PREFIX`, `JOB_NUMBER_PADDING` — job number format, e.g. `RAZ-2026-00001`.
- `CORS_ORIGINS`, `DEFAULT_ACTOR`.
- `JWT_SECRET_KEY`, `JWT_EXPIRY_MINUTES` — sign/expire worker portal login tokens. **Change
  `JWT_SECRET_KEY` before deploying anywhere real** — the default is dev-only.

`.env` is never committed (see `.gitignore`).

### Database migration

Requires a running PostgreSQL instance reachable at `DATABASE_URL`:

```bash
uv run alembic upgrade head
```

### Seed data

Idempotent — safe to run more than once. Seeds the Lahore→Dubai air lane, three customers,
three inquiries carried to different points in the workflow (a draft quote, an accepted
shipment in transit, and an accepted shipment marked at risk), the six worker areas, and a
demo worker account per area:

```bash
uv run python -m seeds.seed
```

**Demo worker logins** (all share the password `Worker123!`):

| Username | Area | Stage they complete |
|---|---|---|
| `ayesha.docs` | Documentation | docs_filed |
| `bilal.pickup` | Pickup | picked_up |
| `zara.transit` | Transit | in_transit |
| `omar.customs`, `sana.customs` | Customs | customs_clearance |
| `hina.arrival` | Arrival | arrived |
| `faisal.delivery` | Delivery | delivered |

Demo-only credentials for local development — not meant for any real deployment.

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

## Frontend setup

Requires Node.js 20+.

```bash
cd frontend
npm install
npm run dev       # starts Vite on http://localhost:5173
```

The dev server proxies `/api/*` to `http://localhost:8000` (see `vite.config.ts`), so run
the backend (`uv run uvicorn app.main:app --reload`, seeded per above) alongside it — no
CORS configuration needed in dev. For a non-dev deployment, set `VITE_API_BASE_URL` to the
backend's URL.

- `npm run build` — type-checks (`tsc -b`) and produces a production bundle in `dist/`.
- `npm run lint` — oxlint.

### Pages

- `/shipments` — ops dashboard: every shipment, filterable by stage / at-risk.
- `/shipments/:id` — shipment detail: status history, advance-to-next-stage, the
  status-correction dialog, at-risk toggle, and reference management. Unauthenticated
  (`current_actor`) — ops retains full override access; see "Worker portal & areas" below
  for why this isn't the primary way stages get marked anymore.
- `/quotes/new` → `/quotes/:id` — pick or create a customer, enter the inquiry, generate a
  quote, override line items while in draft, then send/accept. Accepting shows the
  generated job number and links straight to the new shipment.
- `/workers` — admin: create worker accounts, assign them to an area, deactivate accounts.
- `/worker/login` → `/worker/queue` — the worker portal (real login required; see below).
- `/track` → `/track/:reference` — the public, unauthenticated customer view. Looks up by
  job number or any reference (MAWB/HAWB/MBL/HBL/container) and renders only what
  `GET /tracking/{reference}` returns — no pricing, no internal notes, no risk reason ever
  reaches this page, by construction on the backend.

### Design system

Colors, spacing, and typography are CSS variables in `src/index.css` (light + dark, both
WCAG AA-checked) — a professional navy/slate palette with semantic status colors
(job progress = blue, delivered = green, at-risk = amber), Lexend for headings and Source
Sans 3 for body text. The stage order and human-readable labels are fetched once from
`GET /meta/stages` (`useStages` hook) and never hardcoded in a component — the backend's
`app/models/enums.py` is still the single source of truth for that mapping.

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

POST      /auth/login                  worker login -> bearer token
GET       /auth/me                     resolve the current token to a worker

GET       /worker/queue                requires a worker token; shipments waiting for their area
POST      /worker/shipments/{id}/complete   advances the shipment into the worker's area stage

GET       /areas                       admin, unauthenticated (same trust level as ops)
GET/POST  /workers · PATCH /workers/{id}    admin: create/list/(de)activate worker accounts
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

## Worker portal & areas

Each operational stage after `job_opened` (docs_filed, picked_up, in_transit,
customs_clearance, arrived, delivered) has one **Area** — Documentation, Pickup, Transit,
Customs, Arrival, Delivery. A **Worker** account belongs to exactly one Area. Any worker in
an Area can see and act on any shipment waiting for that Area's stage — "anyone in Customs"
rather than one fixed person per stage, so a warehouse team can share the queue.

A worker signs in at `/worker/login` (real username/password — the only part of the app
with actual authentication; see `app/security.py` for JWT + bcrypt) and lands on
`/worker/queue`: every shipment currently sitting one stage before theirs, oldest first.
Marking one "Done" calls `POST /worker/shipments/{id}/complete`, which is a thin wrapper
around the same `services.transitions.advance_stage` the ops status-update endpoint uses,
with the worker's area stage as the fixed target and the worker's name as the actor. That
reuse is what enforces the restriction — a worker can never advance a shipment into any
stage but their own, because `advance_stage` already rejects anything that isn't the
shipment's immediate next stage; there's no separate authorization check to keep in sync.

Admins manage accounts at `/workers` (`POST /workers`, `PATCH /workers/{id}` to
deactivate/reassign) — that side stays unauthenticated like the rest of ops, matching
`current_actor`. Ops retains the ability to update shipment status directly too (for
corrections, or if a worker's terminal is down); the worker portal is the intended primary
path, not the only one.

## Air freight only

Raaziq currently only forwards air freight. `TransportMode` still has `sea` and `road` in
the schema (so the data model doesn't need to change if that expands later), but no rate
card exists for either, the quote form only offers Air, and the ops shipment list has no
mode filter — there's nothing else to filter by right now.

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

Ops-side login (still `current_actor`, unauthenticated — only the worker portal has real
accounts), predictive ETA, AI pricing or shipment prediction, GPS/IoT, live WeBOC/PSW
integration, ShipsGo/carrier API integration, multi-carrier RFQ automation, live spot-rate
feeds, accounting/ERP, invoicing, payments, microservices, event buses, Redis, Celery,
Kubernetes.
