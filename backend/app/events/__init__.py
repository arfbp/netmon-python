"""Internal event bus (pub/sub) definitions and event payload
schemas. Decouples monitors (producers) from services/websocket
(consumers) so, e.g., the incident engine can react to a PingResult
event without the ping monitor knowing incidents exist."""
