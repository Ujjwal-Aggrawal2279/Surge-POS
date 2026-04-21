import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  // Chunks are served from /assets/surge/dist/ — must match so dynamic imports resolve correctly
  base: "/assets/surge/dist/",
  plugins: [
    react({
      babel: {
        plugins: [["babel-plugin-react-compiler", {}]],
      },
    }),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "../surge/public/dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "surge.js",
        manualChunks: (id) => {
          if (id.includes("node_modules/react") || id.includes("node_modules/react-dom") || id.includes("node_modules/scheduler")) return "vendor";
          if (id.includes("node_modules/@tanstack/react-query")) return "query";
          if (id.includes("node_modules/lucide-react") || id.includes("node_modules/@radix-ui")) return "ui";
        },
        chunkFileNames: "surge-[hash].js",
        assetFileNames: (info) =>
          info.names?.[0]?.endsWith(".css") ? "surge.css" : "surge-[hash][extname]",
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/assets": "http://localhost:8000",
    },
  },
});
