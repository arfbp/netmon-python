"""Unit tests for app.core.config.Settings.

Every test constructs Settings(_env_file=None, **overrides) directly, so
none of them depend on (or pollute) a real .env file — see
tests/conftest.py for why.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


class TestDefaults:
    def test_loads_with_all_defaults(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.app_env == "development"
        assert settings.ping.interval_seconds == 2.0
        assert settings.dns.interval_seconds == 30.0
        assert settings.http.interval_seconds == 15.0
        assert settings.speedtest.interval_seconds == 3600.0

    def test_default_ping_targets(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.ping.targets == ["1.1.1.1", "8.8.8.8"]

    def test_optional_fields_default_to_none(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.ping.isp_gateway is None
        assert settings.alerts.webhook_url is None


class TestCsvListParsing:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("1.1.1.1,8.8.8.8", ["1.1.1.1", "8.8.8.8"]),
            (" 1.1.1.1 , 8.8.8.8 ", ["1.1.1.1", "8.8.8.8"]),  # whitespace tolerated
            ("1.1.1.1,,8.8.8.8", ["1.1.1.1", "8.8.8.8"]),  # empty entries dropped
            ("1.1.1.1", ["1.1.1.1"]),  # single value, no comma
        ],
    )
    def test_ping_targets_csv_parsing(self, raw: str, expected: list[str]) -> None:
        settings = Settings(_env_file=None, ping_targets=raw)
        assert settings.ping.targets == expected

    def test_list_passthrough_when_already_a_list(self) -> None:
        settings = Settings(_env_file=None, ping_targets=["9.9.9.9"])
        assert settings.ping.targets == ["9.9.9.9"]


class TestBlankOptionalFields:
    def test_blank_isp_gateway_becomes_none(self) -> None:
        settings = Settings(_env_file=None, ping_isp_gateway="")
        assert settings.ping.isp_gateway is None

    def test_whitespace_only_isp_gateway_becomes_none(self) -> None:
        settings = Settings(_env_file=None, ping_isp_gateway="   ")
        assert settings.ping.isp_gateway is None

    def test_populated_isp_gateway_is_kept(self) -> None:
        settings = Settings(_env_file=None, ping_isp_gateway="192.168.1.1")
        assert settings.ping.isp_gateway == "192.168.1.1"


class TestThresholdValidation:
    def test_valid_ordering_passes(self) -> None:
        settings = Settings(
            _env_file=None,
            threshold_latency_warning_ms=50,
            threshold_latency_high_ms=100,
            threshold_latency_critical_ms=200,
        )
        assert settings.thresholds.latency_warning_ms == 50

    def test_warning_greater_than_high_raises(self) -> None:
        with pytest.raises(ValidationError, match="warning < high < critical"):
            Settings(
                _env_file=None,
                threshold_latency_warning_ms=150,
                threshold_latency_high_ms=100,
                threshold_latency_critical_ms=300,
            )

    def test_high_equal_to_critical_raises(self) -> None:
        with pytest.raises(ValidationError, match="warning < high < critical"):
            Settings(
                _env_file=None,
                threshold_latency_warning_ms=50,
                threshold_latency_high_ms=300,
                threshold_latency_critical_ms=300,
            )

    def test_packet_loss_warning_greater_than_critical_raises(self) -> None:
        with pytest.raises(ValidationError, match="Packet loss thresholds"):
            Settings(
                _env_file=None,
                threshold_packet_loss_warning_pct=20,
                threshold_packet_loss_critical_pct=10,
            )


class TestAlertValidation:
    def test_alerts_enabled_without_webhook_raises(self) -> None:
        with pytest.raises(ValidationError, match="ALERT_WEBHOOK_URL"):
            Settings(_env_file=None, alerts_enabled=True, alert_webhook_url=None)

    def test_alerts_enabled_with_webhook_passes(self) -> None:
        settings = Settings(
            _env_file=None,
            alerts_enabled=True,
            alert_webhook_url="https://hooks.example.com/x",
        )
        assert settings.alerts.enabled is True

    def test_alerts_disabled_without_webhook_passes(self) -> None:
        settings = Settings(_env_file=None, alerts_enabled=False)
        assert settings.alerts.webhook_url is None


class TestInvalidValues:
    def test_invalid_log_level_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, app_log_level="VERBOSE")  # type: ignore[arg-type]

    def test_negative_interval_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, ping_interval_seconds=-1)

    def test_packet_loss_out_of_range_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, threshold_packet_loss_warning_pct=150)


class TestGroupedViews:
    def test_ping_group_reflects_flat_fields(self) -> None:
        settings = Settings(_env_file=None, ping_interval_seconds=5.0)
        assert settings.ping.interval_seconds == 5.0

    def test_grouped_views_are_frozen(self) -> None:
        settings = Settings(_env_file=None)
        with pytest.raises(AttributeError):
            settings.ping.interval_seconds = 99.0  # type: ignore[misc]


class TestGetSettingsSingleton:
    def test_returns_same_instance(self, isolated_env: pytest.MonkeyPatch) -> None:
        get_settings.cache_clear()
        first = get_settings()
        second = get_settings()
        assert first is second

    def test_cache_clear_produces_new_instance(self, isolated_env: pytest.MonkeyPatch) -> None:
        get_settings.cache_clear()
        first = get_settings()
        get_settings.cache_clear()
        second = get_settings()
        assert first is not second
