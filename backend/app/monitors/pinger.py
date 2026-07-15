"""Default ICMP pinger, wrapping icmplib.

Contract: `default_pinger()` never raises. Any failure — permission
denied (no raw-socket privilege), DNS lookup failure, a socket error —
is treated the same as a network timeout: returns `None`, logged once.
`PingMonitor` doesn't need to distinguish "the target didn't respond"
from "this process can't ping at all"; both mean "no data this tick"
from its perspective, though the log line preserves the distinction for
whoever is debugging why every target always times out on a given
machine (the most common cause: not running with the privileges
`icmplib`'s raw-ICMP mode needs — see `PING_PRIVILEGED` in `.env.example`).
"""

from __future__ import annotations

from icmplib import async_ping
from icmplib.exceptions import ICMPLibError

from app.core.logging import get_logger

logger = get_logger(__name__)


async def default_pinger(address: str, timeout_seconds: float, privileged: bool) -> float | None:
    """Sends one ICMP echo request. Returns round-trip latency in
    milliseconds, or `None` if it timed out or failed for any reason."""
    try:
        host = await async_ping(
            address, count=1, timeout=timeout_seconds, privileged=privileged
        )
    except ICMPLibError:
        logger.exception("pinger.icmp_error", extra={"target": address})
        return None
    except Exception:
        logger.exception("pinger.unexpected_error", extra={"target": address})
        return None

    if not host.is_alive:
        return None
    return host.avg_rtt
