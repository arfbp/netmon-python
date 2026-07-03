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
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.database.session import dispose_engine, init_models

logger = get_logger(__name__)


def _build_lifespan(settings: Settings):  # type: ignore[no-untyped-def]
    """Returns a lifespan context manager closed over a specific
    `Settings` instance, rather than reading `get_settings()` again
    inside the lifespan body — so a `Settings` passed explicitly to
    `create_app()` (e.g. in tests) is what startup/shutdown actually
    use, not whatever `.env` happens to be on disk."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.logging)
        logger.info("app.startup", extra={"env": settings.app_env})

        if settings.app_env == "development":
            # Dev convenience only. Staging/production schema changes go
            # through `alembic upgrade head` (Step 3) — never create_all()
            # — so schema history stays auditable outside development.
            await init_models(settings.database, echo=settings.app_debug)

        yield

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

    app = FastAPI(
        title="NetMon API",
        description="Local network monitoring dashboard — REST + WebSocket API",
        version="0.1.0",
        lifespan=_build_lifespan(resolved_settings),
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

    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
