"""HTTP/WebSocket entrypoints. Routers only — no business logic.

Contract: functions here parse/validate input (via Pydantic schemas),
call a service, and serialize the response. Never talk to
repositories or models directly, never contain monitoring logic.

Modules:
    exception_handlers.py   Converts raw exceptions into the API's
                             standard JSON error envelope. The only
                             place that happens.
    websocket.py             The /ws endpoint — connect, heartbeat,
                              disconnect. Mounted at app root, not
                              versioned under v1 (see its own docstring).
    v1/                      Versioned REST router package.
"""
