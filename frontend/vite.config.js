import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,      // listen on 0.0.0.0 so Docker port mapping works
    port: 3000,
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
