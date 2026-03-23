import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './e2e',  // ✅ E2E tests DEVEM estar em frontend/e2e/
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',
    timeout: 60 * 1000, // 60s global timeout
    expect: {
        timeout: 10 * 1000,
    },
    use: {
        baseURL: process.env.E2E_BASE_URL,
        trace: 'on-first-retry',
    },

    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],

    webServer: {
        command: '../.venv/bin/python -m uvicorn backend.main:app --app-dir .. --host 0.0.0.0 --port 8000',
        url: 'http://localhost:8000',
        reuseExistingServer: true,
        timeout: 120 * 1000,
        env: {
            TESTING: 'True',
            USE_E2E_MOCKS: 'True',
        }
    },
});
