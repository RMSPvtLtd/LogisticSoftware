# Raaziq Sea — Container Tracking Backend

The sea vertical's first feature: a customer enters a container number and gets its
tracking status and full voyage detail. The first (and currently only) data source is SAPT
(South Asia Pakistan Terminals) — but SAPT is never visible to the user, and never called
from the browser. Everything about SAPT is isolated behind a provider abstraction so a
second terminal, port, or shipping line can be added later without rewriting the tracker.

**This is backend-only.** There is no `sea/frontend/` — the customer-facing UI for sea
tracking lives in [`../air/frontend`](../air/frontend)'s public tracking page, as an
Air/Sea toggle, so customers have one page and one URL for tracking either kind of
shipment rather than two separate sites. Air's dev server proxies `/sea-api/*` to this
backend (see `../air/frontend/vite.config.ts`) — the browser only ever talks to air's
frontend origin, never to this backend directly, and never to SAPT. This backend is
otherwise still a fully separate project (own `pyproject.toml`/`uv.lock`, own process, own
port) from air's — see [`../README.md`](../README.md) for how the two verticals relate,
and why the UI is unified while the backends stay independent.

## Architecture

```
Browser (air's frontend origin, :5173)
   │
   ▼
POST /sea-api/tracking          (air's Vite dev server -- proxied server-side,
   │                              not a cross-origin browser request; see
   │                              air/frontend/vite.config.ts)
   ▼
POST /api/tracking               (this backend, :8001 — never SAPT, never
   │                               reached directly from the browser)
   ▼
services.tracking_service.track_container()
   │
   ▼
integrations.tracking.protocol.TrackingProvider   (SAPT is the only implementation today)
   │
   ▼
integrations.tracking.sapt.SAPTProvider
   │
   ├─ GET  .../Enquiries/ContainerHistory   → one record per voyage: status + gate/
   │                                          load/discharge timestamps
   └─ POST .../Enquiries/ContainerDetails   → one call per voyage's `pid`, richer
                                              per-voyage detail (owner, BL, vessel/
                                              voyage, ETA/ETD, seals, commodity, ...)
   │
   ▼
Normalized TrackingResult (schemas/tracking.py) — provider-independent shape
   │
   ▼
air/frontend's TrackingPage (Sea mode): status + timeline + one detail card per voyage
```

Adding a second provider means writing a new module under `backend/integrations/` (its own
subfolder, the way `tracking/` holds SAPT) that satisfies the same `TrackingProvider`
protocol and registering it in `services/tracking_service.py`'s `_PROVIDERS` list — nothing
in the API layer or the frontend needs to know it exists.

## Backend

FastAPI, no database (see "No persistence, on purpose" below).

```
sea/
├── pyproject.toml, uv.lock, .env.example   the backend project root
├── backend/
│   ├── main.py, config.py                   app factory, settings
│   ├── api/tracking.py                        the one route: POST /api/tracking
│   ├── schemas/tracking.py                     TrackingResult, TrackingEvent,
│   │                                           ContainerDetail — the provider-
│   │                                           independent shape nothing upstream
│   │                                           of a provider connector may deviate from
│   ├── services/tracking_service.py             provider selection (currently trivial:
│   │                                             one provider, SAPT)
│   ├── integrations/
│   │   ├── tracking/
│   │   │   ├── protocol.py                          the TrackingProvider protocol
│   │   │   └── sapt.py                               the only SAPT-aware code in the app
│   │   └── {airlines,airports,customs,notifications}/  placeholders — no other
│   │                                                    terminal/carrier integration exists yet
│   ├── utils/
│   │   ├── validation.py                            container number format validation
│   │   ├── cache.py                                  in-memory short-TTL cache
│   │   └── errors.py                                 domain exceptions -> HTTP mapping
│   └── repositories/, workers/, models/               placeholders — no repository
│                                                       layer, background workers, or ORM
│                                                       models exist (no database either
│                                                       -- see "No persistence" below)
├── ai/                                        placeholder — no AI features exist yet
├── database/                                  placeholder — see "No persistence" below
└── tests/                                     44 unit + integration tests (pytest)
```

### Run it

```bash
cd sea-and-air/sea
uv sync --extra dev
cp .env.example .env
uv run uvicorn main:app --app-dir backend --reload --port 8001
```

```bash
uv run pytest -q
```

### No persistence, on purpose

There is no database in this vertical yet. Every lookup is a live, on-demand call to the
provider (short-TTL cache only, no polling — see Phase 9 of the integration plan this was
built against). `database/` is scaffolded and empty; add a real store when something
actually needs one (e.g. search history, saved containers, a second provider that needs
its own reference data) rather than pre-building it speculatively.

## Frontend

There isn't one here — see "This is backend-only" above. The UI lives in
[`../air/frontend/src/pages/TrackingPage.tsx`](../air/frontend/src/pages/TrackingPage.tsx),
which renders an Air/Sea toggle and, in Sea mode, calls this backend through the proxy
(`../air/frontend/src/lib/api/client.ts`'s `seaTrackingApi`). The result/timeline/detail-
card components it uses (`ContainerTimeline.tsx`, `ContainerDetailCard.tsx`) live alongside
it in `air/frontend/src/components/shared/` — reusing air's own design tokens and shadcn
primitives, so it reads as the same product rather than a bolted-on second app.

To run the full sea tracking experience locally, both this backend (`:8001`, below) and
air's frontend + backend (`:5173` / `:8000`, see `../air/README.md`) need to be running —
`/track/sea` on air's frontend is the entry point.

- `/track` — Air mode (default).
- `/track/sea` — Sea mode search form.
- `/track/sea/:containerNumber` — Sea mode search + result (shareable/bookmarkable URL).

### What the page shows

- **Status** — the most recent status code across all of a container's voyages, shown
  as-is (see "Status codes" below).
- **Timeline** — every Gate In / Gate Out / Loading / Discharging event across every
  voyage, most-recent-first.
- **Voyage Details** — one card per voyage/cycle the container has been through (a
  container can have several — e.g. an earlier import leg and a later export leg), each
  with everything SAPT's own per-voyage detail view exposes: owner, BL/shipping bill
  number, container size/type, vessel/voyage, ETA/ETD, gate/discharge/load times, DO
  issuance/expiry, origin/destination, seal numbers, custom status, current position,
  commodity, weight, weighment, and scanning status.

## Status codes

SAPT returns short status codes (`XF`, `IF`, ...) whose meanings haven't been verified
against SAPT documentation. Rather than guess, `SAPT_STATUS_MAP` in `backend/integrations/tracking/sapt.py`
starts empty and every code is displayed as-is until a mapping is confirmed and added
there — see that file's comments before adding one.

## Production readiness

**Technical status.** SAPT's `ContainerHistory` and `ContainerDetails` endpoints are
technically accessible with a plain server-side request carrying no cookies and no browser
session state — verified manually against the live service while building this.

**Integration status.** Raaziq Sea uses SAPT as an external tracking data provider,
isolated behind the `TrackingProvider` protocol described above.

**Operational consideration.** Technical accessibility does not mean SAPT has authorized
automated commercial consumption of these endpoints. The provider architecture exists
specifically so `backend/integrations/tracking/sapt.py` can be replaced with a real, authorized SAPT
integration (or removed) without touching the API, the service layer, or the frontend.
Do not add authentication bypass, CAPTCHA bypass, rate-limit evasion, or any other access-
control circumvention to this connector if SAPT introduces one — replace the connector
with an authorized integration instead, or stop offering SAPT as a provider.
