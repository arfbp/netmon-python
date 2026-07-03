Alembic migration environment, wired against the app's own Settings and
model metadata — see `env.py` for details.

Common commands (run from `backend/`):

    alembic revision --autogenerate -m "add ping_history table"
    alembic upgrade head
    alembic downgrade -1
    alembic current
    alembic history

The database URL is never set in `alembic.ini` — it's resolved from
`DATABASE_URL` (via `.env` / `app.core.config.get_settings()`) every
time, so migrations always target whatever environment is active.

