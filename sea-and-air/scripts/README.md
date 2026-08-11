# Scripts

Cross-vertical operational scripts. Empty for now — today's only scripts (running
migrations, seeding demo data) are vertical-specific and live at `air/alembic.ini` /
`air/database/seeds/seed.py`. Put something here only once a script needs to operate
across both `air/` and `sea/` at once (e.g. spinning up both dev servers together).

- `database/` — cross-vertical DB scripts (e.g. "reset every vertical's dev DB").
- `development/` — local dev tooling shared by both verticals.
- `deployment/` — deploy scripts, once there's somewhere to deploy to.
