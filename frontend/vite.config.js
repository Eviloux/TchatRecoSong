import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    headers: {
      'Cross-Origin-Embedder-Policy': 'unsafe-none'
    }
  }
})
