"""Shared enums used across every layer of the application.

Contract: this module imports nothing from the rest of `app`. Any type
that models/, services/, monitors/, and the API schemas all need to agree
on lives here — the single source of truth for status vocabulary, so
`Severity.CRITICAL` means the same thing in a DB column, a WebSocket
message, and a dashboard color lookup.
"""

from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    """Health classification for a single measurement or an aggregate window.

    Ordered worst-to-best is NOT the member declaration order (StrEnum
    doesn't guarantee ordering semantics); use `Severity.rank()` for any
    comparison logic ("is this worse than that"), never rely on enum
    declaration order or `<`/`>`.
    """

    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
    OFFLINE = "offline"

    @classmethod
    def rank(cls, severity: "Severity") -> int:
        """Return a sortable rank; higher = worse. Used to pick the worst
        severity across multiple simultaneous measurements (e.g. 4 ping
        targets) without depending on enum member order."""
        order = {
            cls.EXCELLENT: 0,
            cls.GOOD: 1,
            cls.WARNING: 2,
            cls.HIGH: 3,
            cls.CRITICAL: 4,
            cls.OFFLINE: 5,
        }
        return order[severity]

    @classmethod
    def worst(cls, severities: "list[Severity]") -> "Severity":
        """Return the worst (highest-rank) severity in a collection.
        Raises ValueError on an empty list rather than silently returning
        a default — callers must not assume "no data" means "excellent"."""
        if not severities:
            raise ValueError("Cannot determine worst severity of an empty collection")
        return max(severities, key=cls.rank)


class MonitorType(StrEnum):
    """Identifies which monitor produced a given result/event.
    Used as a discriminator on events and as a foreign-key-like tag on
    Incidents (which monitor detected it)."""

    PING = "ping"
    DNS = "dns"
    HTTP = "http"
    SPEEDTEST = "speedtest"
    TRACEROUTE = "traceroute"
    TCPDUMP = "tcpdump"


class IncidentStatus(StrEnum):
    """Lifecycle state of an Incident record, per the brief's incident
    lifecycle: Started -> Active -> Recovered."""

    STARTED = "started"
    ACTIVE = "active"
    RECOVERED = "recovered"


class IncidentType(StrEnum):
    """Classification of *why* an incident was opened — drives which
    diagnostics (traceroute/tcpdump) auto-trigger and how the dashboard
    labels the timeline entry."""

    INTERNET_SLOW = "internet_slow"
    PACKET_LOSS = "packet_loss"
    DNS_FAILURE = "dns_failure"
    INTERNET_DOWN = "internet_down"
    GATEWAY_DOWN = "gateway_down"


class AlertChannel(StrEnum):
    """Supported alert delivery channels. Only WEBHOOK has a working
    integration in this phase (Step 11 is architecture-only for the
    rest, per the brief) — the others exist so AlertRule/Settings shapes
    don't need to change when they're implemented."""

    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    WEBHOOK = "webhook"
