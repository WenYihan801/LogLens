/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the Vite server proxies /api and /health to FastAPI, so the
// browser talks to a single origin and no CORS setup is needed.
const API_TARGET = process.env.VITE_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: true },
      "/health": { target: API_TARGET, changeOrigin: true },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Keep the charting library in its own cacheable chunk.
        manualChunks: { charts: ["recharts"], react: ["react", "react-dom", "react-router-dom"] },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
