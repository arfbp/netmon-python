"""Shared pytest fixtures.

The single most important fixture here is `isolated_env`: without it,
`Settings()` would read whatever `.env` file (or real environment
variables) happen to exist on the machine running the tests, making
config tests flaky/order-dependent. Every test that touches `Settings`
must use it.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.core.config import get_settings


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    """Clears the get_settings() cache before and after the test.

    Note: this fixture does NOT prevent Settings from reading a real
    `.env` file in the working directory — pydantic-settings has no env
    var to disable that. Tests that need guaranteed-clean defaults must
    construct `Settings(_env_file=None, **overrides)` directly rather
    than relying on `get_settings()`, which is what every test below
    does. This fixture's job is purely to stop test pollution via the
    lru_cache on `get_settings` itself.
    """
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()
