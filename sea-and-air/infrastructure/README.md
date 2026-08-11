# Infrastructure

Deployment/environment configuration (Docker, IaC, env-specific settings) for each
environment tier. Empty for now — both verticals currently run locally only (`uv run
uvicorn` / `npm run dev`); nothing has been deployed yet, so there's nothing
environment-specific to configure.

- `development/` — local/dev environment config, if it ever needs to be more than each
  vertical's own `.env.example`.
- `staging/`, `production/` — populate once there's an actual staging/production target.
