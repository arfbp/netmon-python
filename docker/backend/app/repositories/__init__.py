"""Data-access layer. One repository per model, each subclassing
`BaseRepository[ModelT]` (base.py) so services can be unit-tested with
an in-memory fake instead of a real database. Repositories are the ONLY
layer allowed to write SQLAlchemy queries.

Per-model repositories are added alongside the services/monitors that
first need them, not speculatively:
    base.py                      BaseRepository[ModelT] generic CRUD.
    ping_history_repository.py   PingHistoryRepository (Step 6).
"""
