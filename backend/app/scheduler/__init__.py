"""Owns the lifecycle of all monitor asyncio tasks: startup,
graceful shutdown, crash isolation/restart-on-failure per monitor,
and on-demand triggering (e.g. traceroute-on-incident)."""
