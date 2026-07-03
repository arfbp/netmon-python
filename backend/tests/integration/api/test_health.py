"""Integration tests for app.main.create_app().

Every test builds its own app via create_app(settings) with an isolated
tmp_path SQLite file — no shared state between tests, no dependency on
a real .env, and lifespan (startup/shutdown) is driven explicitly via
`app.router.lifespan_context`, since httpx's ASGITransport does not run
it automatically the way Starlette's TestClient does.
"""

from __future__ import annotations

from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    defaults = {
        "database_url": f"sqlite+aiosqlite:///{tmp_path}/test.db",
        "app_env": "development",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


class TestAppFactory:
    """Synchronous — building the app / inspecting its config doesn't
    need an event loop, so this class is deliberately not marked
    asyncio, unlike the classes below that make real ASGI requests."""

    def test_create_app_with_default_settings_does_not_raise(self) -> None:
        # Uses real get_settings() / .env resolution — just confirms the
        # factory itself is wired correctly, independent of DB access.
        app = create_app()
        assert app.title == "NetMon API"

    def test_create_app_with_explicit_settings_overrides_get_settings_dep(
        self, tmp_path: Path
    ) -> None:
        from app.core.config import get_settings

        settings = _settings(tmp_path)
        app = create_app(settings)
        assert app.dependency_overrides[get_settings]() is settings

    def test_cors_middleware_configured_with_settings_origins(self, tmp_path: Path) -> None:
        settings = _settings(tmp_path, cors_allowed_origins=["https://example.com"])
        app = create_app(settings)
        cors_middlewares = [m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"]
        assert len(cors_middlewares) == 1


class TestHealthEndpoint:
    async def test_returns_200_ok_with_connected_database(self, tmp_path: Path) -> None:
        app = create_app(_settings(tmp_path))
        transport = ASGITransport(app=app)
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["database"] == "connected"
        assert "timestamp" in body

    async def test_lifespan_creates_tables_in_development(self, tmp_path: Path) -> None:
        """In app_env=development, startup runs init_models() — confirms
        the health check isn't accidentally passing only because SELECT 1
        doesn't need any table to exist."""
        import sqlite3

        settings = _settings(tmp_path)
        app = create_app(settings)
        async with app.router.lifespan_context(app):
            pass

        db_file = tmp_path / "test.db"
        assert db_file.exists()
        con = sqlite3.connect(str(db_file))
        tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
        con.close()
        assert "ping_history" in tables
        assert "incidents" in tables


class TestErrorHandling:
    async def test_unknown_route_returns_404(self, tmp_path: Path) -> None:
        app = create_app(_settings(tmp_path))
        transport = ASGITransport(app=app)
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/does-not-exist")
        assert response.status_code == 404

    async def test_generic_exception_handler_hides_detail_when_debug_false(
        self, tmp_path: Path
    ) -> None:
        """Registers a throwaway route that always raises, to prove the
        generic handler's debug-gating behavior without depending on any
        real endpoint accidentally erroring."""
        settings = _settings(tmp_path, app_debug=False)
        app = create_app(settings)

        @app.get("/api/v1/__boom")
        async def boom() -> None:
            raise RuntimeError("sensitive internal detail")

        # raise_app_exceptions=False: Starlette's ServerErrorMiddleware
        # re-raises the original exception after sending the response
        # (so it reaches server-side logs) — a real ASGI server (uvicorn)
        # swallows that at the protocol layer, but httpx's ASGITransport
        # propagates it to the caller unless told not to. We're testing
        # the response body our handler produced, not exception plumbing.
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/__boom")

        assert response.status_code == 500
        body = response.json()
        assert body["error"] == "internal_server_error"
        assert "sensitive internal detail" not in body["detail"]

    async def test_generic_exception_handler_shows_detail_when_debug_true(
        self, tmp_path: Path
    ) -> None:
        settings = _settings(tmp_path, app_debug=True)
        app = create_app(settings)

        @app.get("/api/v1/__boom")
        async def boom() -> None:
            raise RuntimeError("sensitive internal detail")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/__boom")

        assert response.status_code == 500
        body = response.json()
        assert "sensitive internal detail" in body["detail"]
