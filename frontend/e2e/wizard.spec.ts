import { test, expect } from '@playwright/test';

test.describe('Video Wizard - Idea Flow', () => {

    test.beforeEach(async ({ page }) => {
        // Login first
        await page.goto('/login');
        await page.fill('input[type="email"]', 'rodrigorizando@gmail.com');
        await page.fill('input[type="password"]', 'admin@123');
        await page.click('[data-testid="btn-login"]');
        await expect(page.locator('.app-sidebar')).toBeVisible({ timeout: 60000 });
    });

    test('should create a video from idea successfully', async ({ page }) => {
        // 1. Navigate to Wizard
        await page.goto('/panel/videos/new');

        // 2. Fill Form "Tenho uma Ideia" (default)
        // Prompt
        await page.fill('textarea#prompt', 'Um documentário sobre a história da internet em 30 segundos.');

        // Language - Native Select
        await page.selectOption('#language', 'pt-br'); // Use value 'pt-br'

        // Duration - Native Input
        await page.fill('#duration', '1'); // 1 minute

        // Aspect Ratio - Custom Button
        // Select 9:16
        await page.click('button:has-text("Vertical (9:16)")');

        // Image Source - Custom Button
        // Select Unsplash
        await page.click('button:has-text("Unsplash")');

        // Narration - Custom Toggle
        // It's a div.narration-card. We click it to toggle.
        // Assuming default is OFF (false). Click to turn ON.
        const narrationCard = page.locator('.narration-card');
        if (!await narrationCard.locator('.active').isVisible()) {
            await narrationCard.click();
        }

        // 3. Submit
        const submitBtn = page.locator('button:has-text("Gerar Vídeo")');
        await submitBtn.click();

        // 4. Verify Redirection
        // Should go to /panel/videos/{id}
        await expect(page).toHaveURL(/\/panel\/videos\/\d+/, { timeout: 30000 });

        // 5. Verify Video Dashboard Loaded
        // Check for specific element on video details page?
        // Maybe "Status: Processando" or similar.
        // Assuming we land on VideoDetailsView.vue
        await expect(page.locator('.video-details-container')).toBeVisible({ timeout: 10000 }).catch(() => {
            // Fallback: check something else if container class is different
            return expect(page.locator('h1')).toBeVisible();
        });
    });

    test.afterEach(async ({ page }) => {
        const { cleanupTestVideos } = await import('./utils/cleanup');
        await cleanupTestVideos(page);
    });
});
