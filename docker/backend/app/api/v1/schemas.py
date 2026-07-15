"""Response schemas for the ping REST endpoints.

Kept separate from the ORM model (`app.models.PingHistory`) per Step 3's
rule: models are persistence-shape only. This is the wire shape — it
happens to mirror the model closely today, but that's incidental, not
guaranteed to stay true (e.g. `id` is deliberately omitted here; the
dashboard has no use for it).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.core.enums import Severity


class PingLatestResponse(BaseModel):
    target: str
    timestamp: datetime
    latency_ms: float | None
    is_timeout: bool
    jitter_ms: float | None
    rolling_avg_ms: float | None
    packet_loss_pct: float
    severity: Severity
