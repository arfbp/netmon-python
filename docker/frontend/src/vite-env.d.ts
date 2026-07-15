/// <reference types="vite/client" />

// Contract: every VITE_-prefixed var in .env.example must have a
// corresponding entry here. This is what makes `import.meta.env.VITE_X`
// a compile error instead of `undefined` at runtime when a var is
// renamed or removed — the frontend equivalent of the backend's
// Settings validation.
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_WS_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
