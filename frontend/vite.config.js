import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react(),
    // Remove crossorigin attributes — they break script/css loading
    // when the frontend is served via file:// protocol in Electron.
    {
      name: 'remove-crossorigin',
      transformIndexHtml(html) {
        return html.replace(/\s*crossorigin(?:="[^"]*")?/g, '')
      },
    },
  ],
  base: './',
  server: {
    allowedHosts: true,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
