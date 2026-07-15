"""Application entrypoint.

Contract: `create_app()` is the ONLY place that wires together config,
logging, database lifecycle, CORS, exception handlers, and routers. Run
with `uvicorn app.main:app` for production/dev, or import `create_app`
directly in tests to build an isolated instance with injected `Settings`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import generic_exception_handler, validation_exception_handler
from app.api.v1.router import api_v1_router
from app.api.websocket import router as websocket_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.database.session import dispose_engine, get_sessionmaker, init_models, upgrade_database
from app.events.bus import EventBus
from app.monitors.ping_monitor import PingMonitor
from app.scheduler.monitor_scheduler import MonitorScheduler
from app.websocket.connection_manager import ConnectionManager
from app.websocket.event_forwarder import register_event_forwarding

logger = get_logger(__name__)


def _build_lifespan(settings: Settings, event_bus: EventBus, scheduler: MonitorScheduler):  # type: ignore[no-untyped-def]
    """Returns a lifespan context manager closed over this app's specific
    `Settings`/`EventBus`/`MonitorScheduler` instances, rather than
    reading `get_settings()` again inside the lifespan body — so a
    `Settings` passed explicitly to `create_app()` (e.g. in tests) is
    what startup/shutdown actually use, not whatever `.env` happens to
    be on disk."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.logging)
        logger.info("app.startup", extra={"env": settings.app_env})

        if settings.app_env == "development":
            # Dev convenience only. Staging/production schema changes go
            # through `alembic upgrade head` (Step 3) — never create_all()
            # — so schema history stays auditable outside development.
            await init_models(settings.database, echo=settings.app_debug)
        else:
            upgrade_database(settings.database)

        if settings.monitors_enabled:
            session_factory = get_sessionmaker(settings.database, echo=settings.app_debug)
            scheduler.register(PingMonitor(settings, session_factory, event_bus))
            scheduler.start_all()
            logger.info(
                "app.monitors_started", extra={"monitors": scheduler.registered_monitor_names}
            )

        yield

        if settings.monitors_enabled:
            await scheduler.stop_all()

        logger.info("app.shutdown")
        await dispose_engine(settings.database)

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory.

    Passing an explicit `settings` (tests do this) both drives the
    lifespan hooks AND overrides the `get_settings` DI provider, so
    every layer of the app — routes, lifespan, exception handlers —
    sees exactly that one Settings instance, never a mix of "the one I
    was given" and "whatever get_settings() resolves to right now".
    """
    resolved_settings = settings or get_settings()

    connection_manager = ConnectionManager()
    event_bus = EventBus()
    scheduler = MonitorScheduler()
    register_event_forwarding(event_bus, connection_manager)

    app = FastAPI(
        title="NetMon API",
        description="Local network monitoring dashboard — REST + WebSocket API",
        version="0.1.0",
        lifespan=_build_lifespan(resolved_settings, event_bus, scheduler),
        # Deliberately NOT passing debug=resolved_settings.app_debug here:
        # Starlette's ServerErrorMiddleware, when debug=True, returns its
        # own HTML traceback page and skips any registered Exception
        # handler entirely — wrong shape for a JSON API, and it would
        # silently bypass generic_exception_handler below. Our handler
        # already gates how much detail to reveal off `app_debug` itself
        # (see api/exception_handlers.py), so the API's error responses
        # stay consistently JSON in every environment.
    )

    # Exception handlers read app.state.settings (see
    # api/exception_handlers.py) since Depends() isn't available there.
    app.state.settings = resolved_settings

    # App-lifetime singletons (one per process, not one per request —
    # see core/deps.py's ConnectionManagerDep docstring for why this
    # differs from the DB session pattern).
    app.state.connection_manager = connection_manager
    app.state.event_bus = event_bus
    app.state.scheduler = scheduler

    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(websocket_router)
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
