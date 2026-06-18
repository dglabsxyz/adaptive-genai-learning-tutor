import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
  build: {
    // Split heavy vendor libraries into their own cacheable chunks so the main
    // app bundle stays well under Vite's 500 kB warning threshold. recharts
    // (which bundles d3) is by far the largest dependency.
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'react-query': ['@tanstack/react-query'],
          charts: ['recharts'],
        },
      },
    },
  },
})
