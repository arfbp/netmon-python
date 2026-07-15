"""SQLAlchemy ORM models — one file per aggregate
(ping_history.py, dns_history.py, http_history.py, speed_test.py,
incident.py, traceroute.py, tcp_capture.py, alert.py, setting.py).
Models are persistence-shape only: no business logic, no monitor code.

Contract: importing this package (`from app import models`) has the
side effect of registering every model class on `Base.metadata` — this
is required for both Alembic's `--autogenerate` and `init_models()` to
see every table. Anything that needs the full schema present (Alembic's
`env.py`, `database.session.init_models()`, test fixtures) imports this
package, not an individual model module, even if it only uses one model
directly.
"""

from __future__ import annotations

from app.models.alert import Alert, AlertStatus
from app.models.dns_history import DNSHistory
from app.models.http_history import HTTPHistory
from app.models.incident import Incident
from app.models.ping_history import PingHistory
from app.models.setting import Setting
from app.models.speed_test_history import SpeedTestHistory
from app.models.tcp_capture import CaptureStatus, TcpCapture
from app.models.traceroute_result import TracerouteResult

__all__ = [
    "Alert",
    "AlertStatus",
    "CaptureStatus",
    "DNSHistory",
    "HTTPHistory",
    "Incident",
    "PingHistory",
    "Setting",
    "SpeedTestHistory",
    "TcpCapture",
    "TracerouteResult",
]
