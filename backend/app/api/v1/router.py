"""Aggregates every v1 sub-router into one. `main.py` mounts this once
under the `/api/v1` prefix — individual routers (health, and later
ping/incidents/settings/...) don't set their own top-level prefix
beyond their own resource name (`/health`, `/incidents`, ...).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health, incidents, ping

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(incidents.router)
api_v1_router.include_router(ping.router)
