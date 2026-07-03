"""Cross-cutting application concerns: settings, logging setup,
security, dependency-injection providers, and app-wide constants/enums
(e.g. Severity, MonitorType). Nothing here imports from services/
or monitors/ — this package sits below everything else.

Modules:
    enums.py     Shared vocabulary (Severity, MonitorType, IncidentStatus,
                 IncidentType, AlertChannel). Zero internal dependencies.
    config.py    Typed, validated, env-driven Settings + get_settings()
                 singleton provider + FastAPI dependency alias.
    logging.py   Structured JSON logging setup, driven by Settings.
    deps.py      Shared FastAPI dependency type aliases (SettingsDep, ...).
"""
