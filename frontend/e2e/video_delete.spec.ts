import { test, expect } from '@playwright/test';

test.describe('Video Deletion Flow', () => {
    test.beforeEach(async ({ page }) => {
        // Login before each test
        await page.goto('/login');
        await page.fill('input[type="email"]', 'rodrigorizando@gmail.com');
        await page.fill('input[type="password"]', 'admin@123');
        await page.click('[data-testid="btn-login"]');
        await expect(page).toHaveURL(/\/panel/, { timeout: 15000 });
    });

    test('should delete a video from dashboard list', async ({ page }) => {
        // Create a specific video to delete
        const uniqueTitle = `Excluir Dashboard ${Date.now()}`;
        await page.goto('/panel/videos/new');
        await page.fill('textarea#prompt', uniqueTitle);
        await page.click('button:has-text("Gerar Vídeo")');
        await expect(page).toHaveURL(/\/panel\/videos\/\d+/, { timeout: 30000 });

        // Go back to dashboard
        await page.goto('/panel');

        // Find the specific video
        let videoItem = page.locator('.video-item', { hasText: uniqueTitle });
        try {
            await expect(videoItem).toBeVisible({ timeout: 15000 });
        } catch (e) {
            console.log(`Video '${uniqueTitle}' not found, reloading dashboard...`);
            await page.reload();
            videoItem = page.locator('.video-item', { hasText: uniqueTitle });
            await expect(videoItem).toBeVisible({ timeout: 15000 });
        }

        // Hover and click delete
        await videoItem.hover();
        const deleteBtn = videoItem.locator('[data-testid="delete-video-btn"]');

        try {
            await expect(deleteBtn).toBeVisible({ timeout: 5000 });
        } catch (e) {
            await page.screenshot({ path: 'test-results/dashboard_delete_fail.png' });
            throw e;
        }

        // Click delete
        await deleteBtn.click();

        // Wait for it to disappear
        await expect(videoItem).not.toBeVisible({ timeout: 10000 });
    });

    test('should delete a video from detail view', async ({ page }) => {
        // Create a specific video to delete
        const uniqueTitle = `Excluir Detail ${Date.now()}`;
        await page.goto('/panel/videos/new');
        await page.fill('textarea#prompt', uniqueTitle);
        await page.click('button:has-text("Gerar Vídeo")');
        await expect(page).toHaveURL(/\/panel\/videos\/\d+/, { timeout: 30000 });

        // We are already on detail view
        // Find delete button in header
        const deleteBtn = page.locator('[data-testid="delete-video-btn"]');
        try {
            await expect(deleteBtn).toBeVisible({ timeout: 5000 });
        } catch (e) {
            await page.screenshot({ path: 'test-results/detail_delete_fail.png' });
            throw e;
        }

        // Click delete
        await deleteBtn.click();

        // Should redirect back to panel
        await expect(page).toHaveURL(/\/panel/, { timeout: 15000 });
    });
});
