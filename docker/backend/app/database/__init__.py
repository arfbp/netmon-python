"""Database engine/session lifecycle (SQLAlchemy async engine,
sessionmaker, Base declarative class) and Alembic wiring.
Contract: only repositories/ are allowed to import Session usage
patterns from here; services/ receive sessions via DI, they don't
construct them.

Modules:
    base.py     Declarative Base + naming convention for stable Alembic diffs.
    mixins.py   Reusable column mixins (IntPKMixin, CreatedAtMixin).
    session.py  Async engine/sessionmaker, get_db_session() dependency,
                init_models() (dev/test only — production uses Alembic).
"""
