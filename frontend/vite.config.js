import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,      // listen on 0.0.0.0 so Docker port mapping works
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/config': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/login': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/journal': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/portfolio': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/radar': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/workflows': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/healthz': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/analyze': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    }
  },
  preview: {
    host: true,
    port: 3000,
  },
  build: {
    // Split heavy vendors into cacheable chunks instead of one 1MB bundle.
    // (Vite 8 / rolldown: function-form manualChunks.)
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('recharts')) return 'charts'
            if (id.includes('lightweight-charts')) return 'lwcharts'
            if (id.includes('react')) return 'react'
            return 'vendor'
          }
        },
      },
    },
  },
})
