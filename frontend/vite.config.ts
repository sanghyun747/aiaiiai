import { searchForWorkspaceRoot } from 'vite';
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5317,
    fs: {
      allow: [searchForWorkspaceRoot(process.cwd())],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8317',
        changeOrigin: false,
      },
      '/p': {
        target: 'http://127.0.0.1:8317',
        changeOrigin: false,
      },
      '/comfyui': {
        target: 'http://127.0.0.1:8188',
        changeOrigin: false,
        rewrite: (path) => path.replace(/^\/comfyui/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    css: true,
  },
});
