import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {

    test('should login successfully with valid credentials', async ({ page }) => {
        // Validation: Print console logs to stdout
        page.on('console', msg => console.log(`BROWSER LOG: ${msg.text()}`));
        page.on('pageerror', exception => console.log(`BROWSER ERROR: ${exception}`));

        await page.goto('/login');

        // Fill credentials
        await page.fill('input[type="email"]', 'rodrigorizando@gmail.com');
        await page.fill('input[type="password"]', 'admin@123');

        // Submit
        await page.click('[data-testid="btn-login"]');

        // Verify redirection to panel
        await expect(page).toHaveURL(/\/panel/, { timeout: 15000 });

        // Verify sidebar element (more robust than text)
        await expect(page.locator('.app-sidebar')).toBeVisible({ timeout: 10000 });
        await expect(page.locator('text=Criar Vídeo')).toBeVisible();
    });

    test('should show error with invalid credentials', async ({ page }) => {
        await page.goto('/login');

        await page.fill('input[type="email"]', 'invalid@example.com');
        await page.fill('input[type="password"]', 'WrongPass123');
        await page.click('[data-testid="btn-login"]');

        // Wait for error message
        const errorMsg = page.locator('.error-message');
        await expect(errorMsg).toBeVisible({ timeout: 10000 });

        // Log the text closely
        const text = await errorMsg.textContent();
        console.log(`ERROR MESSAGE FOUND: ${text}`);
    });

    test('should redirect to login when accessing protected route', async ({ page }) => {
        await page.context().clearCookies(); // Ensure logout
        await page.goto('/panel/videos');

        // Should redirect to login
        await expect(page).toHaveURL(/\/login/);
    });

    test('should logout successfully', async ({ page }) => {
        // 1. Login first
        await page.goto('/login');
        await page.fill('input[type="email"]', 'rodrigorizando@gmail.com');
        await page.fill('input[type="password"]', 'admin@123');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL(/\/panel/);

        // 2. Perform Logout
        // Verified selector from Sidebar.vue
        const logoutBtn = page.locator('.logout-btn');
        await expect(logoutBtn).toBeVisible();
        await logoutBtn.click();

        // 3. Verify redirection to login
        await expect(page).toHaveURL(/\/login/);
    });
});
