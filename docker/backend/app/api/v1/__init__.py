"""Version 1 of the REST/WebSocket API surface.

Versioning the API namespace from day one avoids breaking existing
dashboard clients when the schema evolves in v2+.

Modules:
    router.py    Aggregates every sub-router; mounted once in main.py.
    health.py    GET /health — server + database liveness check.
"""
