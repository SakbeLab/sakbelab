import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The build is served by the SakbeLab backend (FastAPI), so it lands inside the
// Python package and ships with it. `npm run dev` proxies the API to a local backend.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "../backend/sakbe/web", emptyOutDir: true, chunkSizeWarningLimit: 1200 },
  server: {
    proxy: {
      "/api": { target: "http://127.0.0.1:8080", ws: true },
    },
  },
});
