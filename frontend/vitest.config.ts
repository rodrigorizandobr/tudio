import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

export default defineConfig({
    plugins: [vue()],
    test: {
        globals: true,
        environment: 'happy-dom',
        setupFiles: ['./src/test/setup.ts'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            exclude: [
                'node_modules/',
                'src/**/*.spec.ts',
                'src/**/*.test.ts',
                '**/*.d.ts',
                'vite.config.ts',
            ],
            thresholds: {
                lines: 85,
                functions: 85,
                branches: 85,
                statements: 85,
            },
        },
        exclude: [
            'e2e/**',
            'node_modules/**',
        ],
    },
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
})
