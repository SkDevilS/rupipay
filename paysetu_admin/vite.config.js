import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { copyFileSync } from 'fs'

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'copy-assets',
      closeBundle() {
        // Copy logo files to dist folder after build
        try {
          copyFileSync('paysetu.png', 'dist/paysetu.png')
          copyFileSync('icon.png', 'dist/icon.png')
          copyFileSync('favicon.png', 'dist/favicon.png')
          console.log('✓ Logo files copied to dist/')
        } catch (err) {
          console.error('Error copying logo files:', err)
        }
      }
    }
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
