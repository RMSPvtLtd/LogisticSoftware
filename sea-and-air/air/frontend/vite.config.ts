import path from "node:path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    proxy: {
      // The sea backend's own routes are already prefixed with /api (see
      // sea-and-air/sea/backend/api/tracking.py), so this rewrite maps
      // /sea-api/tracking -> :8001/api/tracking -- checked before the
      // plain /api rule below, since /sea-api also starts with /api.
      "/sea-api": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/sea-api/, "/api"),
      },
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
})
