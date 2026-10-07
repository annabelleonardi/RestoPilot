import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Share the dev server over a cloudflared quick tunnel (URL changes per run).
    allowedHosts: [".trycloudflare.com"],
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
