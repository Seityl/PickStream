import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";
import proxyOptions from "./proxyOptions";

export default defineConfig({
  base: "/pick_stream/", // Set the base path
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      includeAssets: ['./icons/favicon.ico', './icons/apple-touch-icon.png', './icons/mask-icon.svg'],
      manifest: {
        // Your manifest configuration
      },
      devOptions: {
        enabled: true, // Enable service worker in development
      },
      workbox: {
        cacheId: 'pick-stream-v2', // Change this to force a cache update
        runtimeCaching: [
          {
            urlPattern: ({url}) => {
              return url.pathname.startsWith("/pick_stream");
            },
            handler: "CacheFirst",
            options: {
              cacheName: "pick_stream_cache",
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          }
        ]
      }
    })
  ],
  server: {
    port: 8080,
    proxy: proxyOptions,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    outDir: "../pick_stream/public/frontend",
    emptyOutDir: true,
    target: "es2015"
  }
});
