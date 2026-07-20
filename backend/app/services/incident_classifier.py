"""Pure incident classification helpers.

This module contains zero I/O and zero application state so it can be
unit-tested exhaustively in isolation from the reactive IncidentService.
"""

from __future__ import annotations

from app.core.config import ThresholdConfig
from app.core.enums import IncidentType, Severity


def _is_latency_healthy(severity: Severity) -> bool:
    return severity in (Severity.EXCELLENT, Severity.GOOD)


def _is_latency_bad(severity: Severity) -> bool:
    return severity in (Severity.WARNING, Severity.HIGH, Severity.CRITICAL)


def classify_incident_type(
    target: str,
    severity: Severity,
    packet_loss_pct: float,
    is_gateway_target: bool,
    all_internet_targets_offline: bool,
    thresholds: ThresholdConfig,
) -> IncidentType | None:
    """Returns the incident type for the current measurement, or None
    when the target is healthy enough that no incident should be open.

    Precedence is intentional:
    gateway-down and internet-down outrank per-target quality issues;
    packet-loss outranks latency if latency is still healthy; latency
    only classifies as slow when packet loss is low.
    """
    del target  # target is part of the signature for readability and future context-sensitive rules.

    if is_gateway_target and severity == Severity.OFFLINE:
        return IncidentType.GATEWAY_DOWN

    if all_internet_targets_offline and not is_gateway_target and severity == Severity.OFFLINE:
        return IncidentType.INTERNET_DOWN

    if _is_latency_healthy(severity) and packet_loss_pct >= thresholds.packet_loss_warning_pct:
        return IncidentType.PACKET_LOSS

    if _is_latency_bad(severity) and packet_loss_pct < thresholds.packet_loss_warning_pct:
        return IncidentType.INTERNET_SLOW

    return None