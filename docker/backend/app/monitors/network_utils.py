"""Default gateway detection, for `PING_GATEWAY_AUTO_DETECT`.

Contract: `detect_default_gateway()` never raises — gateway detection is
a best-effort convenience (per the brief: "Gateway ... configurable"),
not something that should crash the Ping Monitor if it fails on an
unusual network setup, a container without route visibility, or a
platform quirk in the underlying library. Every failure mode is caught,
logged once, and results in `None` — callers fall back to pinging only
the explicitly configured targets.
"""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


def detect_default_gateway() -> str | None:
    """Returns the default IPv4 gateway address, or `None` if it can't
    be determined for any reason (library missing, no default route,
    permission issue, unsupported platform)."""
    try:
        import netifaces
    except ImportError:
        logger.warning("network_utils.netifaces_not_installed")
        return None

    try:
        gateways = netifaces.default_gateway()
        ipv4_gateway = gateways.get(netifaces.AF_INET)
        if ipv4_gateway is None:
            logger.warning("network_utils.no_default_ipv4_gateway")
            return None
        address, _interface = ipv4_gateway
        return str(address)
    except Exception:
        logger.exception("network_utils.gateway_detection_failed")
        return None
