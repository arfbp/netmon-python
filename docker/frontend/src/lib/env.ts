/**
 * Runtime configuration, resolved once from Vite's import.meta.env.
 *
 * Contract: this is the ONLY module in the frontend allowed to read
 * `import.meta.env` directly. Everything else (the API client and
 * WebSocket client built in later steps) imports `env` from here —
 * mirroring the backend's rule that only `core/config.py` reads
 * `os.environ`.
 *
 * Empty VITE_API_BASE_URL / VITE_WS_BASE_URL are valid and expected in
 * dev (Vite's proxy in vite.config.ts handles /api and /ws), so unlike
 * the backend's Settings this does not fail fast on blank values — it
 * resolves them to relative-origin defaults instead.
 */

interface Env {
  apiBaseUrl: string;
  wsBaseUrl: string;
}

function resolveWsBaseUrl(explicit: string): string {
  if (explicit) return explicit;
  if (typeof window === "undefined") return "";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}

export const env: Env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "",
  wsBaseUrl: resolveWsBaseUrl(import.meta.env.VITE_WS_BASE_URL || ""),
};
