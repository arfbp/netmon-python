"""Unit tests for app.monitors.ping_analytics. Pure functions, zero I/O."""

from __future__ import annotations

import pytest

from app.core.config import ThresholdConfig
from app.core.enums import Severity
from app.monitors.ping_analytics import (
    classify_severity,
    compute_jitter,
    compute_packet_loss_pct,
    compute_rolling_avg,
)


@pytest.fixture
def thresholds() -> ThresholdConfig:
    return ThresholdConfig(
        latency_warning_ms=80,
        latency_high_ms=150,
        latency_critical_ms=300,
        packet_loss_warning_pct=1,
        packet_loss_critical_pct=10,
    )


class TestPacketLossPct:
    def test_empty_window_is_zero(self) -> None:
        assert compute_packet_loss_pct([]) == 0.0

    def test_all_successful_is_zero(self) -> None:
        assert compute_packet_loss_pct([10.0, 12.0, 11.0]) == 0.0

    def test_all_timeouts_is_hundred(self) -> None:
        assert compute_packet_loss_pct([None, None, None]) == 100.0

    def test_partial_loss(self) -> None:
        assert compute_packet_loss_pct([10.0, None, 12.0, None]) == 50.0


class TestRollingAvg:
    def test_empty_window_is_none(self) -> None:
        assert compute_rolling_avg([]) is None

    def test_all_timeouts_is_none(self) -> None:
        assert compute_rolling_avg([None, None]) is None

    def test_averages_only_successful_samples(self) -> None:
        assert compute_rolling_avg([10.0, None, 20.0]) == 15.0

    def test_single_sample(self) -> None:
        assert compute_rolling_avg([42.0]) == 42.0


class TestJitter:
    def test_empty_window_is_none(self) -> None:
        assert compute_jitter([]) is None

    def test_single_sample_is_none(self) -> None:
        assert compute_jitter([10.0]) is None

    def test_two_consecutive_samples(self) -> None:
        # |10 - 14| = 4
        assert compute_jitter([10.0, 14.0]) == 4.0

    def test_averages_multiple_consecutive_diffs(self) -> None:
        # |10-14|=4, |14-10|=4, |10-20|=10 -> mean = 6.0
        assert compute_jitter([10.0, 14.0, 10.0, 20.0]) == pytest.approx(6.0)

    def test_timeout_breaks_consecutivity(self) -> None:
        # 10 -> None -> 50: no diff computed across the gap, only real
        # consecutive pairs count. Here there are no valid pairs at all.
        assert compute_jitter([10.0, None, 50.0]) is None

    def test_timeout_breaks_but_later_pairs_still_count(self) -> None:
        # 10 -> None -> 50 -> 54: only (50,54) is a valid consecutive pair -> diff 4
        assert compute_jitter([10.0, None, 50.0, 54.0]) == 4.0


class TestClassifySeverity:
    def test_low_latency_no_loss_is_excellent(self, thresholds: ThresholdConfig) -> None:
        # warning_ms/2 = 40; well under that
        result = classify_severity(latency_ms=10.0, packet_loss_pct=0.0, thresholds=thresholds)
        assert result == Severity.EXCELLENT

    def test_upper_half_under_warning_is_good(self, thresholds: ThresholdConfig) -> None:
        # between 40 (warning/2) and 80 (warning)
        result = classify_severity(latency_ms=60.0, packet_loss_pct=0.0, thresholds=thresholds)
        assert result == Severity.GOOD

    def test_between_warning_and_high_is_warning(self, thresholds: ThresholdConfig) -> None:
        result = classify_severity(latency_ms=100.0, packet_loss_pct=0.0, thresholds=thresholds)
        assert result == Severity.WARNING

    def test_between_high_and_critical_is_high(self, thresholds: ThresholdConfig) -> None:
        result = classify_severity(latency_ms=200.0, packet_loss_pct=0.0, thresholds=thresholds)
        assert result == Severity.HIGH

    def test_at_or_above_critical_is_critical(self, thresholds: ThresholdConfig) -> None:
        result = classify_severity(latency_ms=350.0, packet_loss_pct=0.0, thresholds=thresholds)
        assert result == Severity.CRITICAL

    def test_current_timeout_is_critical_not_offline(self, thresholds: ThresholdConfig) -> None:
        """A single dropped probe (this-tick timeout) is CRITICAL, not
        OFFLINE — OFFLINE requires sustained 100% loss across the whole
        window, checked via packet_loss_pct separately."""
        result = classify_severity(latency_ms=None, packet_loss_pct=25.0, thresholds=thresholds)
        assert result == Severity.CRITICAL

    def test_hundred_percent_loss_is_offline(self, thresholds: ThresholdConfig) -> None:
        result = classify_severity(latency_ms=None, packet_loss_pct=100.0, thresholds=thresholds)
        assert result == Severity.OFFLINE

    def test_packet_loss_severity_can_dominate_good_latency(
        self, thresholds: ThresholdConfig
    ) -> None:
        """Excellent latency but crossing the critical packet-loss
        threshold must still report CRITICAL overall — severity is the
        worse of the two dimensions, not just latency."""
        result = classify_severity(latency_ms=5.0, packet_loss_pct=15.0, thresholds=thresholds)
        assert result == Severity.CRITICAL

    def test_packet_loss_warning_threshold_boundary(self, thresholds: ThresholdConfig) -> None:
        result = classify_severity(latency_ms=5.0, packet_loss_pct=1.0, thresholds=thresholds)
        assert result == Severity.WARNING
