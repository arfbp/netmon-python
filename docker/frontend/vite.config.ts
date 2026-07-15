import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Full implementation deferred — this is the structural placeholder for
// Step 1. Behavior to wire up in a later step:
//   - dev server proxy for /api and /ws to the FastAPI backend, so the
//     frontend never hardcodes a backend origin
//   - @ alias resolution matching tsconfig.app.json
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
