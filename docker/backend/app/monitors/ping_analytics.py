"""Pure ping analytics — jitter, rolling average, packet loss %, and
severity classification.

Contract: every function here is pure (no I/O, no state) and operates on
a plain sequence of recent samples. `PingMonitor` owns the actual rolling
window (a `deque` per target) and calls these functions each tick; this
module has no knowledge of asyncio, icmplib, the database, or the event
bus, which is what makes it trivial to unit test exhaustively.

A "sample" is `float | None`: a latency in milliseconds, or `None` for a
timed-out probe.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.config import ThresholdConfig
from app.core.enums import Severity


def compute_packet_loss_pct(samples: Sequence[float | None]) -> float:
    """Percentage of samples in the window that timed out. 0.0 for an
    empty window (no data yet — not evidence of loss)."""
    if not samples:
        return 0.0
    timeouts = sum(1 for s in samples if s is None)
    return (timeouts / len(samples)) * 100.0


def compute_rolling_avg(samples: Sequence[float | None]) -> float | None:
    """Mean of the successful (non-timeout) samples in the window.
    `None` if every sample in the window timed out — there's no
    meaningful average latency for a target that hasn't responded at
    all recently."""
    successful = [s for s in samples if s is not None]
    if not successful:
        return None
    return sum(successful) / len(successful)


def compute_jitter(samples: Sequence[float | None]) -> float | None:
    """Mean absolute difference between consecutive successful samples
    (RFC 3550-style jitter approximation). Timeouts break consecutivity
    — a latency right before a timeout and one right after aren't
    treated as "consecutive" for jitter purposes, since the gap itself
    is the packet-loss signal, not a jitter signal. `None` if fewer than
    two consecutive successful samples exist anywhere in the window.
    """
    diffs: list[float] = []
    previous: float | None = None
    for sample in samples:
        if sample is None:
            previous = None
            continue
        if previous is not None:
            diffs.append(abs(sample - previous))
        previous = sample

    if not diffs:
        return None
    return sum(diffs) / len(diffs)


def _classify_latency_severity(latency_ms: float | None, thresholds: ThresholdConfig) -> Severity:
    """A timed-out current probe is classified CRITICAL here (not
    OFFLINE) — OFFLINE is reserved for sustained 100% loss across the
    whole window (see `classify_severity`), so a single dropped probe
    on an otherwise healthy target reads as CRITICAL-this-tick rather
    than immediately flipping the target's badge to OFFLINE.

    The EXCELLENT/GOOD split below WARNING isn't independently
    configured (the brief only specifies warning/high/critical
    thresholds) — GOOD occupies the upper half of the "under warning"
    range as a deliberate, documented simplification, so all six
    Severity levels the brief asks for actually get used.
    """
    if latency_ms is None:
        return Severity.CRITICAL
    if latency_ms < thresholds.latency_warning_ms / 2:
        return Severity.EXCELLENT
    if latency_ms < thresholds.latency_warning_ms:
        return Severity.GOOD
    if latency_ms < thresholds.latency_high_ms:
        return Severity.WARNING
    if latency_ms < thresholds.latency_critical_ms:
        return Severity.HIGH
    return Severity.CRITICAL


def _classify_packet_loss_severity(packet_loss_pct: float, thresholds: ThresholdConfig) -> Severity:
    if packet_loss_pct >= 100.0:
        return Severity.OFFLINE
    if packet_loss_pct >= thresholds.packet_loss_critical_pct:
        return Severity.CRITICAL
    if packet_loss_pct >= thresholds.packet_loss_warning_pct:
        return Severity.WARNING
    return Severity.EXCELLENT


def classify_severity(
    *, latency_ms: float | None, packet_loss_pct: float, thresholds: ThresholdConfig
) -> Severity:
    """Overall severity for one probe result: the worse of the
    latency-based and packet-loss-based classifications. Sustained
    100% packet loss in the window always wins as OFFLINE, regardless
    of what a (nonexistent) latency reading would otherwise suggest.
    """
    latency_severity = _classify_latency_severity(latency_ms, thresholds)
    loss_severity = _classify_packet_loss_severity(packet_loss_pct, thresholds)
    return Severity.worst([latency_severity, loss_severity])
