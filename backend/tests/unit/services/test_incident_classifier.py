"""Unit tests for incident classification logic."""

from __future__ import annotations

import pytest

from app.core.config import ThresholdConfig
from app.core.enums import IncidentType, Severity
from app.services.incident_classifier import classify_incident_type


def _thresholds() -> ThresholdConfig:
    return ThresholdConfig(
        latency_warning_ms=80,
        latency_high_ms=150,
        latency_critical_ms=300,
        packet_loss_warning_pct=1,
        packet_loss_critical_pct=10,
    )


@pytest.mark.parametrize(
    ("target", "severity", "packet_loss_pct", "is_gateway_target", "all_internet_targets_offline", "expected"),
    [
        ("192.168.1.1", Severity.OFFLINE, 0.0, True, False, IncidentType.GATEWAY_DOWN),
        ("1.1.1.1", Severity.OFFLINE, 0.0, False, True, IncidentType.INTERNET_DOWN),
        ("1.1.1.1", Severity.GOOD, 1.0, False, False, IncidentType.PACKET_LOSS),
        ("1.1.1.1", Severity.GOOD, 25.0, False, False, IncidentType.PACKET_LOSS),
        ("1.1.1.1", Severity.WARNING, 0.0, False, False, IncidentType.INTERNET_SLOW),
        ("1.1.1.1", Severity.CRITICAL, 0.0, False, False, IncidentType.INTERNET_SLOW),
        ("1.1.1.1", Severity.GOOD, 0.0, False, False, None),
        ("1.1.1.1", Severity.OFFLINE, 0.0, False, False, None),
        ("1.1.1.1", Severity.WARNING, 15.0, False, False, None),
    ],
)
def test_classify_incident_type_cases(
    target: str,
    severity: Severity,
    packet_loss_pct: float,
    is_gateway_target: bool,
    all_internet_targets_offline: bool,
    expected: IncidentType | None,
) -> None:
    assert (
        classify_incident_type(
            target,
            severity,
            packet_loss_pct,
            is_gateway_target,
            all_internet_targets_offline,
            _thresholds(),
        )
        == expected
    )
