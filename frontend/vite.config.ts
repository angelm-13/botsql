import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// El proxy evita CORS en desarrollo: el frontend pide a /api y Vite lo
// reenvia al backend. En produccion se sirve todo desde el mismo origen y
// no hace falta abrir nada.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: process.env.BI_BACKEND ?? "http://localhost:5001", changeOrigin: true },
    },
  },
});
