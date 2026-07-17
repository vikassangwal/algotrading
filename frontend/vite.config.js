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
})
