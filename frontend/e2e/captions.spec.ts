import { test, expect } from '@playwright/test';

test.describe('Animated Captions Flow', () => {
    test.setTimeout(480000); // 8 minutes total test timeout

    test.beforeEach(async ({ page }) => {
        // Login
        await page.goto('/login');
        await page.fill('input[type="email"]', process.env.TEST_EMAIL!);
        await page.fill('input[type="password"]', process.env.TEST_PASSWORD!);
        await page.click('button:has-text("Entrar")');
        await expect(page.locator('.app-sidebar')).toBeVisible({ timeout: 60000 });

        // Navigate to panel
        await page.goto('/panel');

        // Wait for list to load (max 15s)
        try {
            await page.waitForSelector('.video-item', { timeout: 15000 });
        } catch (e) {
            console.log('Timeout waiting for any video items, reloading...');
            await page.reload();
            await page.waitForSelector('.video-item', { timeout: 15000 }).catch(() => console.log('Still no items after reload.'));
        }

        // Try to find a completed video in the list with the specific test title
        const testTitle = 'Documentário sobre o futuro da IA e legendas animadas.';
        const completedVideo = page.locator('.video-item').filter({ hasText: testTitle }).filter({ hasText: 'completed' }).first();
        if (await completedVideo.isVisible()) {
            await completedVideo.click();
        } else {
            // Create a fresh one with AUTO settings to ensure it completes
            await page.goto('/panel/videos/new');
            await page.fill('textarea#prompt', 'Documentário sobre o futuro da IA e legendas animadas.');

            // Enable Narração IA
            await page.click('.narration-card');

            // Select Unsplash (Automatic Images)
            await page.click('button:has-text("Unsplash")');

            // Generate
            await page.click('button:has-text("Gerar Vídeo")');

            // Wait for redirection
            await expect(page).toHaveURL(/\/panel\/videos\/\d+/, { timeout: 30000 });

            // Wait for completion of all steps including Render
            // In Mock mode this should be relatively fast, but in real mode it can take 4-5 mins
            await expect(page.locator('.step-item.completed:has-text("Render")')).toBeVisible({ timeout: 360000 });
        }

        await expect(page.locator('.processing-timeline')).toBeVisible();
    });

    test('should generate captions for a single scene', async ({ page }) => {
        // Ensure we are on a detail page
        await expect(page).toHaveURL(/\/panel\/videos\/\d+/);

        // Find first scene card
        const sceneCard = page.locator('.scene-card').first();
        await expect(sceneCard).toBeVisible();

        // Click generate caption icon (📝) in the scene footer
        // The title contains "Legenda" but let's use the icon/text approach if possible
        const captionBtn = sceneCard.locator('button:has-text("📝"), button[title*="Legenda"]');
        await captionBtn.click();

        // Check for processing/done state badge in the scene
        await expect(sceneCard.locator('.scene-caption-badge, :has-text("✓ Legenda")').first()).toBeVisible({ timeout: 60000 });
    });

    test('should generate global captions for the whole video', async ({ page }) => {
        // Find caption dashboard card
        const captionCard = page.locator(':has-text("Legendas Animadas")').last();
        await captionCard.scrollIntoViewIfNeeded();

        // Select "Bounce" style
        await page.click('button:has-text("Bounce")');

        // Click "Gerar Legendas"
        const generateBtn = page.locator('button:has-text("Gerar Legendas"), button:has-text("Regenerar")');
        await generateBtn.click();

        // Check timeline for "Legenda" step state
        const captionStep = page.locator('.step-item:has-text("Legenda")');
        await expect(captionStep).toHaveClass(/processing|completed/, { timeout: 15000 });

        // Wait for completion
        await expect(captionStep).toHaveClass(/completed/, { timeout: 120000 });

        // Verify download link appears
        await expect(page.locator('a:has-text("com legenda")').first()).toBeVisible();
    });
});
