"""WebSocket connection manager and outbound message schemas.
Subscribes to the internal event bus and pushes real-time updates
to connected dashboard clients. Never polls the database itself.

Modules:
    schemas.py            WSMessage outbound envelope.
    connection_manager.py ConnectionManager — owns connected clients,
                           the only place that calls send_json.
    event_forwarder.py    Bridges events/bus.py -> ConnectionManager.
                           Registered once at app startup.
"""
