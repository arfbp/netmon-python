# NetMon — Local Network Monitoring Dashboard

Self-hosted, real-time Internet quality monitoring: ping/DNS/HTTP/speedtest
telemetry, automatic incident detection, and on-incident diagnostics
(traceroute, tcpdump), served over a WebSocket-driven React dashboard.

> **Status:** Step 1 of 17 — project structure, dependency management,
> coding standards, and configuration strategy only. No runnable app yet.

## Project layout

```
netmon/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers (v1/) — HTTP+WS entrypoints only
│   │   ├── core/            # settings, logging, DI providers, shared enums
│   │   ├── database/         # async engine/session lifecycle, Alembic wiring
│   │   ├── models/           # SQLAlchemy ORM models, one file per aggregate
│   │   ├── repositories/     # data access — the only layer writing queries
│   │   ├── services/         # domain logic: incidents, alerts, analytics
│   │   ├── monitors/         # independent asyncio monitor tasks
│   │   ├── events/           # internal pub/sub bus + event payload schemas
│   │   ├── websocket/        # connection manager, outbound message schemas
│   │   ├── scheduler/        # monitor task lifecycle, crash isolation
│   │   └── utils/            # stateless helpers only
│   ├── alembic/               # DB migrations (SQLite -> Postgres path)
│   ├── tests/
│   │   ├── unit/              # pure logic, no I/O
│   │   └── integration/       # real SQLite + FastAPI TestClient + WS
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ui/            # shadcn/ui primitives (generated, not hand-authored)
│       │   └── dashboard/     # NOC dashboard composite components
│       ├── pages/
│       ├── hooks/             # React Query hooks, WS subscription hooks
│       ├── lib/                # API client, formatting, WS client
│       ├── store/              # Zustand client-side UI state
│       └── types/              # TS types mirroring backend Pydantic schemas
├── docker/                     # Compose + Dockerfiles (Step 16)
└── README.md
```

## Why this layout (architecture rationale)

**Layered, one-directional dependency flow.**
`monitors/` and `api/` are the only two places allowed to *start* work;
everything else is called, never calls upward. Concretely:

```
api/ ──┐
        ├──> services/ ──> repositories/ ──> database/ ──> models/
monitors/ ──> events/ (publish) ──> services/ + websocket/ (subscribe)
core/  (imported by everyone, imports nothing above it)
```

**Why an event bus between monitors and everything else?**
The brief requires every monitor to run as an independent asyncio task
that never blocks another. If the Ping Monitor directly called
"IncidentService.evaluate()" and "WebSocketManager.broadcast()", it would
own knowledge of — and a hard dependency on — every consumer of its data.
Adding a new consumer (e.g. an alert engine in Step 11) would mean editing
the Ping Monitor. Instead, monitors only publish typed events
(`PingResultEvent`, `PacketLossDetectedEvent`, ...); services and the
WebSocket layer subscribe independently. This is what makes "traceroute
triggers automatically on incident" (Step 13) pluggable later without
touching the Ping Monitor at all.

**Why repositories are a hard boundary.**
Services contain the actual "is this an incident?" / "should this alert
fire?" logic — the part with real unit-test value. If SQLAlchemy queries
leak into services, testing that logic requires a real database. Behind
a repository interface (Protocol), services can be tested against an
in-memory fake in milliseconds, and the SQLite → PostgreSQL migration
(explicitly required by the brief) touches only `database/` and
`repositories/`, never `services/` or `monitors/`.

**Why per-aggregate models/tables instead of one generic `metrics` table.**
Explicitly required by the brief. It also means each history table can
have the *right* schema and indexes (e.g. `PingHistory` needs
per-target latency + jitter + rolling average columns; `HTTPHistory`
needs DNS/TCP/TLS/TTFB breakdown columns) instead of a lossy generic
`(key, value, timestamp)` shape that would make the analytics/history
charts (Step 15) painful to query.

**Why `core/` has zero outgoing internal imports.**
Settings, logging, and shared enums (`Severity`, `MonitorType`,
`IncidentStatus`) are needed by every other package. Keeping `core/`
dependency-free prevents circular imports as the app grows.

## Dependency management

- **Backend:** `pyproject.toml` is the single source of truth (PEP 621).
  Every dependency has an inline comment justifying its inclusion — see
  `backend/pyproject.toml`. Dev-only tooling (pytest, ruff, mypy,
  pre-commit) is isolated under the `dev` extra so production images
  don't install it.
- **Frontend:** `package.json`, pinned with caret ranges; exact versions
  come from the committed lockfile once `npm install` is run.
- **Lockfiles are not generated in this step** (no network installs have
  been run yet) — they will be committed once dependencies are actually
  installed in a later step, so they reflect real resolution output
  rather than a hand-typed guess.

## Configuration strategy

All runtime behavior — targets, intervals, thresholds, network interface,
database URL, retention — is environment-variable driven, never
hardcoded, per the brief. `backend/.env.example` is the authoritative
list of every configurable knob and its default; it exists now (Step 1)
so the *shape* of configuration is fixed before any monitor code is
written against it. The typed `Settings` model (Pydantic Settings,
validated at startup, fails fast on misconfiguration) is implemented in
**Step 2**, along with the same env-driven pattern surfaced to the
frontend at build time via Vite `import.meta.env`.

See `STANDARDS.md` for coding conventions enforced across both stacks.

## Docker deployment

The repository includes a two-container Docker setup under `docker/`:

- `docker/backend.Dockerfile` builds the FastAPI API container
- `docker/frontend.Dockerfile` builds the Nginx static frontend
- `docker/docker-compose.yml` wires them together and reads backend env from `backend/.env` on the host

Start it with:

```bash
cd docker
docker compose up --build -d
```

The frontend is served on `http://localhost:8080` and proxies API/WebSocket traffic to the backend container. Backend config stays outside the image, so you can update `backend/.env` on the host and restart the backend container without rebuilding the backend image.
