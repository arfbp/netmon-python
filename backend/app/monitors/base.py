"""Abstract base for every monitor (Ping, DNS, HTTP, SpeedTest, ...).

Contract: a monitor implements `tick()` — one unit of work (e.g. "ping
every target once") — and nothing else. `BaseMonitor` owns the interval
loop and per-tick exception isolation; task creation/supervision/restart
is the scheduler's job (`scheduler/monitor_scheduler.py`), not this
class's. A monitor never calls another monitor, a service, or the
WebSocket layer directly — it publishes to the event bus and is done.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import ClassVar

from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseMonitor(ABC):
    name: ClassVar[str]

    def __init__(self, interval_seconds: float) -> None:
        self.interval_seconds = interval_seconds
        self._stop_event = asyncio.Event()

    @abstractmethod
    async def tick(self) -> None:
        """One unit of work: e.g. ping every target once, or run one DNS
        resolution round. Raising here is caught by `run_forever()` and
        logged — a single failed tick must never stop future ticks."""

    def request_stop(self) -> None:
        """Signals `run_forever()` to exit after the current tick (or
        immediately, if currently sleeping between ticks). Called by the
        scheduler during app shutdown."""
        self._stop_event.set()

    async def run_forever(self) -> None:
        """Runs `tick()` on `interval_seconds` cadence until
        `request_stop()` is called.

        The sleep between ticks accounts for how long the tick itself
        took (`interval_seconds - elapsed`, floored at 0) so a slow tick
        doesn't compound into ever-increasing drift from the configured
        interval — important for a monitor whose whole purpose is
        precise timing (Ping Monitor at 2s).
        """
        self._stop_event.clear()
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                await self.tick()
            except Exception:
                logger.exception("monitor.tick_failed", extra={"monitor": self.name})

            elapsed = time.monotonic() - started
            remaining = max(0.0, self.interval_seconds - elapsed)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=remaining)
            except TimeoutError:
                pass
