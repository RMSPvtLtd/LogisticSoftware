# Shared

Code and types genuinely common to both `air/` and `sea/` — not a dumping ground for
anything that happens to be similar. Nothing lives here yet; both verticals are still
independent. Promote something here only once it's duplicated between `air/` and `sea/`
and staying in sync matters (e.g. a shared auth/JWT scheme, a common design system, a
customer/company model both verticals reference).

- `frontend/`, `components/`, `types/` — cross-vertical UI building blocks and TS types.
- `backend/`, `schemas/`, `utils/` — cross-vertical Python modules (e.g. a shared
  `portable_enum()` helper, common Pydantic base schemas).
- `auth/` — if air and sea end up under one login system rather than two, it lives here.
- `database/` — cross-vertical DB conventions (e.g. a shared `TimestampMixin`), not a
  shared database — each vertical keeps its own schema/migrations.
- `config/` — shared environment/config conventions.
