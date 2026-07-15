# Coding Standards

These are enforced, not aspirational — via `ruff`/`mypy --strict` (backend)
and `eslint`/`tsc --strict` (frontend) in CI and pre-commit.

## Backend (Python 3.13)

1. **Type hints on every function signature**, including return type.
   `mypy --strict` runs in CI; a missing annotation is a build failure,
   not a warning.
2. **Async everywhere I/O happens.** Any function that touches the
   network, disk, or DB is `async def`. Sync code is reserved for pure
   computation (e.g. jitter/rolling-average math in `monitors/`).
3. **No global mutable state.** Configuration, DB sessions, and the
   event bus are provided via FastAPI's dependency-injection system
   (`Depends(...)`) or constructor injection — never module-level
   singletons reached for by import. This is what makes services
   testable with fakes.
4. **Repositories are the only SQL.** If you're writing a `select()`
   or a `session.execute()` outside `repositories/`, it's in the wrong
   file.
5. **No magic numbers.** Every threshold, interval, and target lives in
   `core/config.py` (Step 2), sourced from environment variables with
   `.env.example` as the documented default. Monitors read thresholds
   from injected `Settings`, not literals.
6. **One reason to change per module** (SRP). A monitor never formats a
   WebSocket message; a repository never decides severity; an API
   router never computes an incident duration.
7. **Structured logging, not `print`.** `logger.info("ping.recorded",
   target=target, latency_ms=latency)` — key-value structured fields,
   not interpolated strings, so logs are machine-parseable (Step 2).
8. **Docstrings on every public class/function** stating *contract*
   (inputs, outputs, side effects, failure modes) — see the
   `__init__.py` files already in place for the expected voice/level of
   detail per package.
9. **Naming:** `snake_case` for functions/variables, `PascalCase` for
   classes, `SCREAMING_SNAKE_CASE` only for true constants in `core/`.
   Event classes suffixed `Event` (`PacketLossDetectedEvent`);
   repository interfaces suffixed `Repository`
   (`PingHistoryRepository`); implementations suffixed `Impl` only
   when a fake/mock counterpart exists for tests.

## Frontend (React + TypeScript)

1. **`strict: true` in tsconfig, no `any`.** Use `unknown` + narrowing,
   or generate/hand-write types under `src/types/` that mirror backend
   Pydantic schemas 1:1 (field names and optionality must match — this
   is checked in review, not just by the compiler).
2. **Server state vs. UI state are different tools.** Anything that
   comes from the API/WebSocket goes through React Query (`hooks/`,
   cache + revalidation). Zustand (`store/`) is only for local UI state
   (e.g. selected time range, sidebar collapsed) that has no server
   source of truth. Don't duplicate server data into Zustand.
3. **`shadcn/ui` components are generated into `components/ui/` via the
   CLI, not hand-written from scratch**, and are not modified beyond
   the generated file except for the theme tokens they consume. Compose
   them in `components/dashboard/`.
4. **No inline hex colors in components.** Severity colors (Excellent →
   Critical/Offline) are Tailwind theme tokens defined once (Step 7),
   referenced by name (`bg-severity-critical`), so a threshold-color
   mapping change is a one-line edit, not a grep-and-replace.
5. **Function components + hooks only.** No class components.
6. **One component, one file, colocated by feature** under
   `components/dashboard/` (e.g. `PingChart.tsx`, `IncidentTimeline.tsx`),
   not grouped by "atoms/molecules/organisms".

## Cross-cutting

- **Conventional commits** (`feat:`, `fix:`, `refactor:`, `test:`,
  `docs:`, `chore:`) — makes a 5-year maintenance history navigable.
- **No TODOs without an issue reference** once the repo has an issue
  tracker; until then, `# TODO(step-N): ...` so deferred work is traced
  to the roadmap step that will address it, per the brief's explicit
  "no placeholder code" rule.
- **Every PR-sized change includes or updates tests.** Backend:
  `pytest`. Frontend: component/hook tests land alongside the dashboard
  step once there's UI to test.
