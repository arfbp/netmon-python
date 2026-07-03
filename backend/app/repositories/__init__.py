"""Data-access layer. One repository per model, each subclassing
`BaseRepository[ModelT]` (base.py) so services can be unit-tested with
an in-memory fake instead of a real database. Repositories are the ONLY
layer allowed to write SQLAlchemy queries.

Per-model repositories (PingHistoryRepository, IncidentRepository, ...)
are added alongside the services/monitors that first need them, not
speculatively — see base.py for why."""
