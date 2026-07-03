"""WebSocket connection manager and outbound message schemas.
Subscribes to the internal event bus and pushes real-time updates
to connected dashboard clients. Never polls the database itself."""
