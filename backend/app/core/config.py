"""Typed application configuration.

Contract: every configurable knob mentioned in the brief (targets,
intervals, thresholds, network interface, database, retention) is a field
on `Settings`, sourced from environment variables / `.env`, validated at
process startup. Nothing outside this module reads `os.environ` directly
— if a piece of code needs a value, it takes `Settings` (or one of its
grouped sub-objects below) as a dependency.

`.env.example` at the repo root is the authoritative list of env var
names and defaults; this file must be kept in sync with it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
AppEnv = Literal["development", "staging", "production"]


def _split_csv(value: object) -> list[str]:
    """Parse a comma-separated env string into a stripped, non-empty list.
    Also accepts an already-parsed list (so tests can construct Settings
    with `ping_targets=["1.1.1.1"]` directly instead of a CSV string)."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    raise TypeError(f"Expected str or list, got {type(value).__name__}")


# ---------------------------------------------------------------------------
# Grouped, read-only convenience views over Settings.
#
# Why: Settings itself stays flat (one field per env var) so it maps 1:1
# onto .env.example with zero renaming/aliasing indirection. But monitor/
# service code reading `settings.ping.interval_seconds` is far more
# readable — and greppable — than `settings.ping_interval_seconds` mixed
# in among 30 unrelated fields. These dataclasses are pure views: they
# hold no state of their own and are rebuilt from Settings on first access.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    url: str
    retention_days: int


@dataclass(frozen=True, slots=True)
class PingConfig:
    targets: list[str]
    gateway_auto_detect: bool
    isp_gateway: str | None
    interval_seconds: float


@dataclass(frozen=True, slots=True)
class DNSConfig:
    test_domains: list[str]
    resolvers: list[str]
    interval_seconds: float


@dataclass(frozen=True, slots=True)
class HTTPConfig:
    test_url: str
    interval_seconds: float


@dataclass(frozen=True, slots=True)
class SpeedTestConfig:
    interval_seconds: float


@dataclass(frozen=True, slots=True)
class ThresholdConfig:
    latency_warning_ms: float
    latency_high_ms: float
    latency_critical_ms: float
    packet_loss_warning_pct: float
    packet_loss_critical_pct: float


@dataclass(frozen=True, slots=True)
class TracerouteConfig:
    on_incident: bool


@dataclass(frozen=True, slots=True)
class TcpDumpConfig:
    on_incident: bool
    interface: str
    max_duration_seconds: int
    storage_dir: Path


@dataclass(frozen=True, slots=True)
class WebSocketConfig:
    heartbeat_seconds: int


@dataclass(frozen=True, slots=True)
class AlertConfig:
    enabled: bool
    webhook_url: str | None


@dataclass(frozen=True, slots=True)
class CORSConfig:
    allowed_origins: list[str]


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: LogLevel
    dir: Path
    debug: bool


class Settings(BaseSettings):
    """Root configuration object. One instance per process, obtained via
    `get_settings()` — never instantiate directly outside of tests."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App -----------------------------------------------------------
    app_env: AppEnv = "development"
    app_debug: bool = True
    app_log_level: LogLevel = "INFO"
    app_log_dir: Path = Path("./logs")

    # --- Database ------------------------------------------------------
    database_url: str = "sqlite+aiosqlite:///./data/netmon.db"
    database_retention_days: int = Field(default=30, gt=0)

    # --- Ping ------------------------------------------------------------
    # NoDecode: these are plain "a,b,c" env strings, not JSON arrays.
    # Without it, pydantic-settings tries `json.loads()` on the raw env
    # value for any list-typed field before our `_parse_csv_list`
    # validator ever runs, and blows up on ordinary comma-separated
    # input. NoDecode defers all decoding to our `mode="before"`
    # validator below.
    ping_targets: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["1.1.1.1", "8.8.8.8"]
    )
    ping_gateway_auto_detect: bool = True
    ping_isp_gateway: str | None = None
    ping_interval_seconds: float = Field(default=2.0, gt=0)

    # --- DNS -------------------------------------------------------------
    dns_test_domains: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["cloudflare.com", "google.com"]
    )
    dns_resolvers: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["1.1.1.1", "8.8.8.8"]
    )
    dns_interval_seconds: float = Field(default=30.0, gt=0)

    # --- HTTP ------------------------------------------------------------
    http_test_url: AnyHttpUrl = AnyHttpUrl("https://www.gstatic.com/generate_204")
    http_interval_seconds: float = Field(default=15.0, gt=0)

    # --- Speed test ------------------------------------------------------
    speedtest_interval_seconds: float = Field(default=3600.0, gt=0)

    # --- Thresholds ------------------------------------------------------
    threshold_latency_warning_ms: float = Field(default=80, gt=0)
    threshold_latency_high_ms: float = Field(default=150, gt=0)
    threshold_latency_critical_ms: float = Field(default=300, gt=0)
    threshold_packet_loss_warning_pct: float = Field(default=1, ge=0, le=100)
    threshold_packet_loss_critical_pct: float = Field(default=10, ge=0, le=100)

    # --- Incident-triggered diagnostics ---------------------------------
    traceroute_on_incident: bool = True
    tcpdump_on_incident: bool = True
    tcpdump_interface: str = "auto"
    tcpdump_max_duration_seconds: int = Field(default=60, gt=0)
    tcpdump_storage_dir: Path = Path("./data/captures")

    # --- WebSocket -------------------------------------------------------
    ws_heartbeat_seconds: int = Field(default=20, gt=0)

    # --- Alerting (architecture only — Step 11) --------------------------
    alerts_enabled: bool = False
    alert_webhook_url: str | None = None

    # --- CORS --------------------------------------------------------------
    # Vite's default dev port (5173) plus the common alt (3000) so a
    # fresh `npm run dev` works against the API with zero config. Set
    # explicitly in .env for any other frontend origin (e.g. a built
    # static bundle served from a different port/domain).
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    # --- Field validators --------------------------------------------------

    @field_validator(
        "ping_targets", "dns_test_domains", "dns_resolvers", "cors_allowed_origins", mode="before"
    )
    @classmethod
    def _parse_csv_list(cls, value: object) -> list[str]:
        return _split_csv(value)

    @field_validator("ping_isp_gateway", "alert_webhook_url", mode="before")
    @classmethod
    def _blank_string_to_none(cls, value: object) -> object:
        """Env vars left blank (`PING_ISP_GATEWAY=`) arrive as `""`, not
        unset — without this, an intentionally-empty optional field would
        fail validation instead of resolving to None."""
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    # --- Cross-field validation --------------------------------------------

    @model_validator(mode="after")
    def _validate_threshold_ordering(self) -> "Settings":
        """Thresholds must be strictly increasing — a Warning threshold
        that's higher than Critical would make the severity classifier
        (Step 6+) produce nonsensical results. Fail at startup, not at
        3am when the first ping comes in."""
        if not (
            self.threshold_latency_warning_ms
            < self.threshold_latency_high_ms
            < self.threshold_latency_critical_ms
        ):
            raise ValueError(
                "Latency thresholds must satisfy: "
                "warning < high < critical "
                f"(got warning={self.threshold_latency_warning_ms}, "
                f"high={self.threshold_latency_high_ms}, "
                f"critical={self.threshold_latency_critical_ms})"
            )
        if not (
            self.threshold_packet_loss_warning_pct < self.threshold_packet_loss_critical_pct
        ):
            raise ValueError(
                "Packet loss thresholds must satisfy: warning < critical "
                f"(got warning={self.threshold_packet_loss_warning_pct}, "
                f"critical={self.threshold_packet_loss_critical_pct})"
            )
        return self

    @model_validator(mode="after")
    def _validate_alert_webhook_present_if_enabled(self) -> "Settings":
        if self.alerts_enabled and self.alert_webhook_url is None:
            raise ValueError(
                "ALERTS_ENABLED=true requires ALERT_WEBHOOK_URL to be set "
                "(no other alert channel is implemented yet — see Step 11)"
            )
        return self

    # --- Grouped read-only views --------------------------------------------
    # cached_property: computed once per Settings instance (which is itself
    # process-lifetime via get_settings()'s lru_cache), not once per access.

    @cached_property
    def database(self) -> DatabaseConfig:
        return DatabaseConfig(url=self.database_url, retention_days=self.database_retention_days)

    @cached_property
    def ping(self) -> PingConfig:
        return PingConfig(
            targets=self.ping_targets,
            gateway_auto_detect=self.ping_gateway_auto_detect,
            isp_gateway=self.ping_isp_gateway,
            interval_seconds=self.ping_interval_seconds,
        )

    @cached_property
    def dns(self) -> DNSConfig:
        return DNSConfig(
            test_domains=self.dns_test_domains,
            resolvers=self.dns_resolvers,
            interval_seconds=self.dns_interval_seconds,
        )

    @cached_property
    def http(self) -> HTTPConfig:
        return HTTPConfig(
            test_url=str(self.http_test_url), interval_seconds=self.http_interval_seconds
        )

    @cached_property
    def speedtest(self) -> SpeedTestConfig:
        return SpeedTestConfig(interval_seconds=self.speedtest_interval_seconds)

    @cached_property
    def thresholds(self) -> ThresholdConfig:
        return ThresholdConfig(
            latency_warning_ms=self.threshold_latency_warning_ms,
            latency_high_ms=self.threshold_latency_high_ms,
            latency_critical_ms=self.threshold_latency_critical_ms,
            packet_loss_warning_pct=self.threshold_packet_loss_warning_pct,
            packet_loss_critical_pct=self.threshold_packet_loss_critical_pct,
        )

    @cached_property
    def traceroute(self) -> TracerouteConfig:
        return TracerouteConfig(on_incident=self.traceroute_on_incident)

    @cached_property
    def tcpdump(self) -> TcpDumpConfig:
        return TcpDumpConfig(
            on_incident=self.tcpdump_on_incident,
            interface=self.tcpdump_interface,
            max_duration_seconds=self.tcpdump_max_duration_seconds,
            storage_dir=self.tcpdump_storage_dir,
        )

    @cached_property
    def websocket(self) -> WebSocketConfig:
        return WebSocketConfig(heartbeat_seconds=self.ws_heartbeat_seconds)

    @cached_property
    def alerts(self) -> AlertConfig:
        return AlertConfig(enabled=self.alerts_enabled, webhook_url=self.alert_webhook_url)

    @cached_property
    def cors(self) -> CORSConfig:
        return CORSConfig(allowed_origins=self.cors_allowed_origins)

    @cached_property
    def logging(self) -> LoggingConfig:
        return LoggingConfig(level=self.app_log_level, dir=self.app_log_dir, debug=self.app_debug)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide Settings singleton. Cached so `.env` is parsed and
    validated exactly once per process, but still reached via DI
    (`Depends(get_settings)`) everywhere rather than imported as a
    module-level global — tests override it with
    `app.dependency_overrides[get_settings] = lambda: Settings(...)`,
    and `get_settings.cache_clear()` resets it between test cases that
    need a fresh instance."""
    return Settings()
