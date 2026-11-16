import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import process from 'node:process'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: process.env.E2E_BACKEND_URL ? {
      '/api/v1': { target: process.env.E2E_BACKEND_URL, changeOrigin: true },
    } : undefined,
  },
})
