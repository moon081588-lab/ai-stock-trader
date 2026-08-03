import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy keeps the frontend origin-agnostic — no CORS juggling in dev.
    proxy: {
      // ws: true is required for /api/v1/ws/prices to upgrade through the proxy.
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true, ws: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
