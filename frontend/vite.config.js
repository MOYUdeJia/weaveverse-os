import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const portFile = path.resolve(__dirname, '../backend/.weaveverse-port')

function readBackendPort() {
  if (process.env.WEAVEVERSE_API_PORT) {
    return process.env.WEAVEVERSE_API_PORT
  }

  try {
    return fs.readFileSync(portFile, 'utf-8').trim()
  } catch {
    return '8765'
  }
}

const backendPort = readBackendPort()

export default defineConfig({
  plugins: [vue()],
  define: {
    __WV_BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  build: {
    emptyOutDir: true,
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
})
