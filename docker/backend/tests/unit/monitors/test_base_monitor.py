"""Unit tests for app.monitors.base.BaseMonitor."""

from __future__ import annotations

import asyncio

from app.monitors.base import BaseMonitor


class _CountingMonitor(BaseMonitor):
    name = "counting"

    def __init__(self, interval_seconds: float) -> None:
        super().__init__(interval_seconds)
        self.tick_count = 0

    async def tick(self) -> None:
        self.tick_count += 1


class _FailingMonitor(BaseMonitor):
    name = "failing"

    def __init__(self, interval_seconds: float) -> None:
        super().__init__(interval_seconds)
        self.tick_count = 0

    async def tick(self) -> None:
        self.tick_count += 1
        raise RuntimeError("tick always fails")


class TestRunForever:
    async def test_ticks_repeatedly_until_stopped(self) -> None:
        monitor = _CountingMonitor(interval_seconds=0.01)
        task = asyncio.create_task(monitor.run_forever())
        await asyncio.sleep(0.05)
        monitor.request_stop()
        await asyncio.wait_for(task, timeout=1)

        assert monitor.tick_count >= 2

    async def test_stops_promptly_after_request_stop(self) -> None:
        monitor = _CountingMonitor(interval_seconds=10.0)  # long interval
        task = asyncio.create_task(monitor.run_forever())
        await asyncio.sleep(0.01)  # let the first tick happen
        monitor.request_stop()
        # Should return almost immediately, not wait out the 10s interval.
        await asyncio.wait_for(task, timeout=1)

    async def test_failing_tick_does_not_stop_the_loop(self) -> None:
        """The core exception-isolation guarantee: a tick that always
        raises must not prevent subsequent ticks from running."""
        monitor = _FailingMonitor(interval_seconds=0.01)
        task = asyncio.create_task(monitor.run_forever())
        await asyncio.sleep(0.05)
        monitor.request_stop()
        await asyncio.wait_for(task, timeout=1)

        assert monitor.tick_count >= 2
