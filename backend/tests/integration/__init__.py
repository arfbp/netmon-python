"""Integration tests: real SQLite (temp file / in-memory), real FastAPI TestClient,
real WebSocket handshake. No real network calls to the internet — ping/http/dns
targets are pointed at local fixtures or mocked sockets."""
