"""Global exception handlers.

Contract: this is the ONLY place a raw exception gets converted into an
HTTP JSON response. Routers/services raise plain exceptions (or
FastAPI's `HTTPException` for expected 4xx cases) — they never construct
a `Response` themselves. Keeping error *shape* centralized here means
every error the API returns has the same `{"error": ..., "detail": ...}`
envelope, which the frontend's API client (built in a later step) can
rely on unconditionally.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": jsonable_encoder(exc.errors())},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for anything not already handled as an `HTTPException`.
    Reads `app.state.settings.app_debug` (set in `main.create_app`)
    rather than calling `get_settings()` directly — exception handlers
    run outside the normal dependency-injection flow, so there's no
    `Depends` available here."""
    settings = getattr(request.app.state, "settings", None)
    debug = bool(settings.app_debug) if settings is not None else False

    logger.error(
        "unhandled_exception",
        extra={"path": str(request.url), "method": request.method, "error": str(exc)},
        exc_info=exc,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": str(exc) if debug else "An unexpected error occurred",
        },
    )
