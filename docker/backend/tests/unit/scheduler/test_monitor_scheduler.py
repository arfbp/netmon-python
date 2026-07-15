"""Unit tests for app.scheduler.monitor_scheduler.MonitorScheduler."""

from __future__ import annotations

import asyncio

from app.monitors.base import BaseMonitor
from app.scheduler.monitor_scheduler import MonitorScheduler


class _CountingMonitor(BaseMonitor):
    name = "counting"

    def __init__(self, interval_seconds: float = 0.01) -> None:
        super().__init__(interval_seconds)
        self.tick_count = 0

    async def tick(self) -> None:
        self.tick_count += 1


class _CrashOnceMonitor(BaseMonitor):
    """Simulates run_forever() itself dying unexpectedly on its first
    invocation (not just a single tick failing, which BaseMonitor
    already isolates) — this is what the scheduler's restart logic
    exists for."""

    name = "crash_once"

    def __init__(self) -> None:
        super().__init__(interval_seconds=0.01)
        self.run_forever_call_count = 0

    async def run_forever(self) -> None:  # type: ignore[override]
        self.run_forever_call_count += 1
        if self.run_forever_call_count == 1:
            raise RuntimeError("simulated crash on first run")
        # Second call: behave like a normal, quickly-stoppable monitor.
        self._stop_event.clear()
        await self._stop_event.wait()

    async def tick(self) -> None:  # pragma: no cover - unused, run_forever overridden
        pass


class TestStartAllAndStopAll:
    async def test_registered_monitor_starts_and_ticks(self) -> None:
        scheduler = MonitorScheduler()
        monitor = _CountingMonitor()
        scheduler.register(monitor)

        scheduler.start_all()
        await asyncio.sleep(0.05)
        await scheduler.stop_all()

        assert monitor.tick_count >= 2

    async def test_stop_all_stops_every_registered_monitor(self) -> None:
        scheduler = MonitorScheduler()
        monitor_a = _CountingMonitor()
        monitor_b = _CountingMonitor()
        scheduler.register(monitor_a)
        scheduler.register(monitor_b)

        scheduler.start_all()
        await asyncio.sleep(0.03)
        await scheduler.stop_all()

        # Both should have ticked at least once and both tasks cleaned up.
        assert monitor_a.tick_count >= 1
        assert monitor_b.tick_count >= 1

    async def test_registered_monitor_names_reflects_registrations(self) -> None:
        scheduler = MonitorScheduler()
        scheduler.register(_CountingMonitor())
        assert scheduler.registered_monitor_names == ["counting"]


class TestCrashRestart:
    async def test_monitor_is_restarted_after_run_forever_crashes(self) -> None:
        scheduler = MonitorScheduler(restart_backoff_seconds=0.01)
        monitor = _CrashOnceMonitor()
        scheduler.register(monitor)

        scheduler.start_all()
        # Give it time to: crash on attempt 1, back off, restart on attempt 2.
        await asyncio.sleep(0.1)
        await scheduler.stop_all()

        assert monitor.run_forever_call_count >= 2
