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
    port: 5174,
    proxy: {
      // The sea backend's own router already prefixes routes with /api
      // (see backend/api/tracking.py), so this forwards as-is -- no
      // stripping, unlike the air frontend's proxy.
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
})
