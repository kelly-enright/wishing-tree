import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The built site is committed and served by FastAPI, so the base path is '/'.
// During development `npm run dev` proxies /api to the Python server on 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  build: { outDir: 'dist' },
})
