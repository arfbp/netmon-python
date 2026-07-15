"""Ping REST endpoints.

Contract: this is deliberately minimal — one read endpoint. Its only job
is giving the dashboard something to render on first load, before the
first WebSocket `ping_result` event arrives (up to `PING_INTERVAL_SECONDS`
later). Full historical queries (1h/24h/7d ranges, per-target time series
for charts) are Step 15's job, using `PingHistoryRepository.get_since()`
(already built in Step 6) — this endpoint only ever needs
`get_recent(limit=1)` per configured target.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.schemas import PingLatestResponse
from app.core.deps import DbSessionDep, SettingsDep
from app.repositories.ping_history_repository import PingHistoryRepository

router = APIRouter(prefix="/ping", tags=["ping"])


@router.get("/latest", response_model=list[PingLatestResponse])
async def get_latest_ping_results(
    session: DbSessionDep, settings: SettingsDep
) -> list[PingLatestResponse]:
    """One row per configured target: its most recent PingHistory entry.
    Targets with no data yet (app just started, first tick hasn't run)
    are simply omitted rather than padded with fake zero-values — the
    frontend treats "target not in the list yet" as its own loading
    state per target.
    """
    repo = PingHistoryRepository(session)
    results: list[PingLatestResponse] = []

    for target in settings.ping.targets:
        rows = await repo.get_recent(target, limit=1)
        if not rows:
            continue
        row = rows[0]
        results.append(
            PingLatestResponse(
                target=row.target,
                timestamp=row.timestamp,
                latency_ms=row.latency_ms,
                is_timeout=row.is_timeout,
                jitter_ms=row.jitter_ms,
                rolling_avg_ms=row.rolling_avg_ms,
                packet_loss_pct=row.packet_loss_pct,
                severity=row.severity,
            )
        )
    return results
