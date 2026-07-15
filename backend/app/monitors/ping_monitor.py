"""The Ping Monitor — the heart of the application, per the brief.

Every `PING_INTERVAL_SECONDS`, pings every configured target (ISP
gateway, auto-detected default gateway, and every address in
`PING_TARGETS`) concurrently, maintains a per-target rolling window for
jitter/rolling-average/packet-loss analytics (`ping_analytics.py`),
writes one `PingHistory` row per target per tick, and publishes one
`PingResultEvent` per target per tick — never storing a bare ping, per
the brief's "Do NOT simply store ping. Store analytics."
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.logging import get_logger
from app.events.bus import EventBus
from app.events.schemas import PingResultEvent
from app.models import PingHistory
from app.monitors.base import BaseMonitor
from app.monitors.network_utils import detect_default_gateway
from app.monitors.ping_analytics import (
    classify_severity,
    compute_jitter,
    compute_packet_loss_pct,
    compute_rolling_avg,
)
from app.monitors.pinger import default_pinger
from app.repositories.ping_history_repository import PingHistoryRepository

logger = get_logger(__name__)

Pinger = Callable[[str, float, bool], Awaitable[float | None]]


class PingMonitor(BaseMonitor):
    name = "ping"

    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        event_bus: EventBus,
        *,
        pinger: Pinger | None = None,
    ) -> None:
        super().__init__(interval_seconds=settings.ping.interval_seconds)
        self._settings = settings
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._pinger: Pinger = pinger or default_pinger

        self.targets = self._resolve_targets()
        self._windows: dict[str, deque[float | None]] = {
            target: deque(maxlen=settings.ping.rolling_window_size) for target in self.targets
        }
        logger.info("ping_monitor.targets_resolved", extra={"targets": self.targets})

    def _resolve_targets(self) -> list[str]:
        """Order: ISP gateway first (if configured), then the
        auto-detected LAN gateway (if enabled), then every explicitly
        configured target — this is also the priority order a human
        reading the dashboard would want when diagnosing "where is the
        problem": LAN first, then WAN, then the internet at large.
        Duplicates (e.g. the auto-detected gateway happens to equal a
        configured target) are removed, preserving first occurrence.
        """
        targets: list[str] = []
        if self._settings.ping.isp_gateway:
            targets.append(self._settings.ping.isp_gateway)
        if self._settings.ping.gateway_auto_detect:
            detected = detect_default_gateway()
            if detected:
                targets.append(detected)
        targets.extend(self._settings.ping.targets)

        seen: set[str] = set()
        deduped: list[str] = []
        for target in targets:
            if target not in seen:
                seen.add(target)
                deduped.append(target)
        return deduped

    async def tick(self) -> None:
        rows = await asyncio.gather(*(self._probe_target(target) for target in self.targets))

        async with self._session_factory() as session:
            repo = PingHistoryRepository(session)
            for row in rows:
                await repo.add(row)
            await session.commit()

        for row in rows:
            await self._event_bus.publish(
                PingResultEvent(
                    occurred_at=row.timestamp,
                    target=row.target,
                    latency_ms=row.latency_ms,
                    is_timeout=row.is_timeout,
                    jitter_ms=row.jitter_ms,
                    rolling_avg_ms=row.rolling_avg_ms,
                    packet_loss_pct=row.packet_loss_pct,
                    severity=row.severity,
                )
            )

    async def _probe_target(self, target: str) -> PingHistory:
        latency_ms = await self._pinger(
            target, self._settings.ping.timeout_seconds, self._settings.ping.privileged
        )

        window = self._windows[target]
        window.append(latency_ms)

        packet_loss_pct = compute_packet_loss_pct(window)
        jitter_ms = compute_jitter(window)
        rolling_avg_ms = compute_rolling_avg(window)
        severity = classify_severity(
            latency_ms=latency_ms,
            packet_loss_pct=packet_loss_pct,
            thresholds=self._settings.thresholds,
        )

        return PingHistory(
            timestamp=datetime.now(UTC),
            target=target,
            latency_ms=latency_ms,
            is_timeout=latency_ms is None,
            jitter_ms=jitter_ms,
            rolling_avg_ms=rolling_avg_ms,
            packet_loss_pct=packet_loss_pct,
            severity=severity,
        )
