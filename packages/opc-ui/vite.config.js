import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    allowedHosts: ['.cpolar.cn', '.cpolar.com', 'localhost'],
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        // 保留 /api 前缀，因为后端路由是 /api/v1/xxx
        // rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
    cors: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
