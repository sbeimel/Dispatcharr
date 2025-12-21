import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';

// https://vite.dev/config/
export default defineConfig({
  // The base URL for the build, adjust this to match your desired path
  plugins: [react()],

  // publicDir: '/data',

  server: {
    host: '0.0.0.0', // Allow external connections (Docker)
    port: 9191,
    watch: {
      usePolling: true, // Better for Docker on Windows
      interval: 1000,
    },

    proxy: {
      "/api": {
        target: "http://localhost:5656", // Backend server
        changeOrigin: true,
        secure: false, // Set to true if backend uses HTTPS
        // rewrite: (path) => path.replace(/^\/api/, ""), // Optional path rewrite
      },
      "/ws": {
        target: "http://localhost:8001", // Backend server
        changeOrigin: true,
        secure: false, // Set to true if backend uses HTTPS
        // rewrite: (path) => path.replace(/^\/api/, ""), // Optional path rewrite
      },
    },
  },

  // Optimize for Windows Docker and Production builds
  optimizeDeps: {
    include: ['react', 'react-dom'],
  },

  // Build optimization for faster builds
  build: {
    target: 'es2015',
    minify: 'esbuild',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
        },
      },
    },
    // Increase chunk size warning limit
    chunkSizeWarningLimit: 1000,
  },

  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setupTests.js'],
    globals: true,
  },
});
