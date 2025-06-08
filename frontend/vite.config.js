import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  
  // Build optimizations
  build: {
    target: 'esnext', // Target modern browsers
    sourcemap: false, // Disable sourcemaps in production
    minify: 'esbuild', // Use esbuild for faster minification
    rollupOptions: {
      output: {
        manualChunks: {
          // Split vendor dependencies
          vendor: ['react', 'react-dom', 'react-router-dom'],
          animations: ['framer-motion'],
          icons: ['react-icons'], // Group all react-icons together
          ui: ['rc-slider', 'swiper']
        }
      }
    }
  },
  
  // Development optimizations - Remove problematic packages
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'framer-motion',
      'lucide-react',
      'react-icons/fa',
      'react-icons/io'
    ]
  },
  
  // Server optimizations
  server: {
    warmup: {
      clientFiles: [
        './src/components/**/*.jsx',
        './src/pages/**/*.jsx',
        './src/hooks/**/*.js'
      ]
    }
  },
  
  // Resolve optimizations
  resolve: {
    extensions: ['.js', '.jsx'] // Reduce extension checks
  }
})
