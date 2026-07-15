"""Owns the lifecycle of every monitor's asyncio task.

Contract: `MonitorScheduler` is the ONLY place `asyncio.create_task()`
is called for a monitor. `BaseMonitor.run_forever()` already isolates
per-tick exceptions (see its docstring), so the supervisor loop here is
defense-in-depth — it exists for the rare case where `run_forever()`
itself exits unexpectedly (a bug, an uncaught cancellation edge case),
restarting that one monitor after a backoff rather than leaving it dead
silently for the rest of the process lifetime.
"""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.monitors.base import BaseMonitor

logger = get_logger(__name__)


class MonitorScheduler:
    def __init__(self, *, restart_backoff_seconds: float = 5.0) -> None:
        self._monitors: list[BaseMonitor] = []
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._restart_backoff_seconds = restart_backoff_seconds

    def register(self, monitor: BaseMonitor) -> None:
        """Must be called before `start_all()` — monitors registered
        after startup are not picked up (no dynamic add/remove in this
        phase; every monitor is known at app startup)."""
        self._monitors.append(monitor)

    def start_all(self) -> None:
        for monitor in self._monitors:
            self._tasks[monitor.name] = asyncio.create_task(
                self._supervise(monitor), name=f"monitor-supervisor:{monitor.name}"
            )
        logger.info("scheduler.started", extra={"monitor_count": len(self._monitors)})

    async def _supervise(self, monitor: BaseMonitor) -> None:
        while True:
            try:
                await monitor.run_forever()
                return  # clean exit via request_stop() during shutdown
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("scheduler.monitor_crashed", extra={"monitor": monitor.name})
                await asyncio.sleep(self._restart_backoff_seconds)

    async def stop_all(self) -> None:
        """Signals every monitor to stop, cancels their supervisor
        tasks, and waits for them to finish. Uses `return_exceptions=True`
        so one task raising during shutdown doesn't prevent the others
        from being awaited (and potentially leaking as a "Task was
        destroyed but it is pending" warning)."""
        for monitor in self._monitors:
            monitor.request_stop()

        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("scheduler.stopped")

    @property
    def registered_monitor_names(self) -> list[str]:
        return [monitor.name for monitor in self._monitors]
