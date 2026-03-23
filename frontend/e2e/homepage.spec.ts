import { test, expect } from '@playwright/test';

/**
 * Basic E2E test example - validates homepage loads correctly
 * 
 * Location: MUST be in frontend/e2e/ directory
 * Run: cd frontend && npx playwright test
 */

test.describe('Homepage', () => {
    test('should load successfully', async ({ page }) => {
        // Navigate to home
        await page.goto('/');

        // Verify page title
        await expect(page).toHaveTitle(/Tudio/);

        // Verify login view container is visible (Root element of LoginView)
        const loginView = page.locator('.login-view');
        await expect(loginView).toBeVisible();
    });

    test('should have login button', async ({ page }) => {
        await page.goto('/');

        // Check for login/sign-in button
        // Using accessible role selector
        const loginButton = page.getByRole('button', { name: 'Entrar' });
        await expect(loginButton).toBeVisible();
    });
});
