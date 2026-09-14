import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5175, // Pinned per-project port (3000 = Next.js apps); must stay in backend cors_origins
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          // React, React-DOM, React Router, Chakra UI, Emotion, and framer-motion
          // are tightly coupled at runtime (shared React internals/singletons).
          // Keep them in one chunk together with vite's own dep-loading helpers
          // to avoid the "Cannot read properties of undefined (reading
          // 'useLayoutEffect')" crash seen when React is split away from them.
          if (
            /node_modules\/(react|react-dom|react-router|react-router-dom|@chakra-ui|@emotion|framer-motion|@popperjs|focus-trap|tabbable|hoist-non-react-statics|scheduler)\//.test(
              id
            )
          ) {
            return 'vendor-ui'
          }
          if (/node_modules\/react-icons\//.test(id)) {
            return 'vendor-icons'
          }
          if (/node_modules\/axios\//.test(id)) {
            return 'vendor-axios'
          }
          if (/node_modules\/@tanstack\/react-query/.test(id)) {
            return 'vendor-query'
          }
          return undefined
        },
      },
    },
  },
})


