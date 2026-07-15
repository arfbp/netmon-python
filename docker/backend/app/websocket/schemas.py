"""Outbound WebSocket message envelope.

Contract: every message pushed to a connected dashboard client uses this
envelope — `type` is what the frontend switches on to dispatch to the
right handler/reducer, `payload` carries the event-specific data (shape
varies per `type`), `timestamp` is server send-time (not necessarily
identical to when the underlying event occurred, though for this app's
sub-second event->broadcast latency the difference is negligible).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class WSMessage(BaseModel):
    type: str
    payload: Any = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
