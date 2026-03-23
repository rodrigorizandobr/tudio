import { test, expect } from '@playwright/test';

test.describe('Video Editor Flow', () => {
    test.setTimeout(180000); // 3 minutes for Real AI / Slow Gen in Prod Mode

    test.beforeEach(async ({ page }) => {
        // Login
        await page.goto('/login');
        await page.fill('input[type="email"]', process.env.TEST_EMAIL!);
        await page.fill('input[type="password"]', process.env.TEST_PASSWORD!);
        await page.click('[data-testid="btn-login"]');
        await expect(page.locator('.app-sidebar')).toBeVisible({ timeout: 60000 }); // Increased for prod mode

        // Submit via UI to ensure Auth and State are correct
        await page.goto('/panel/videos/new');

        // Fill required prompt
        await page.fill('textarea#prompt', 'Teste de edição de vídeo curto (E2E).');

        // Select "Manual" image source to avoid AI generation (Speed up test)
        await page.click('button:has-text("Manual")');

        // Submit
        await page.click('button:has-text("Gerar Vídeo")');

        // Wait for redirection to editor
        await expect(page).toHaveURL(/\/panel\/videos\/\d+/, { timeout: 30000 });

        // Wait for editor to load (check for "Roteiro" step or similar)
        await expect(page.locator('.processing-timeline')).toBeVisible({ timeout: 20000 });
    });

    test('should allow full editor flow (voice direction and scene narration)', async ({ page }) => {
        // --- Part 1: Voice Direction ---
        // 1. Locate Voice Direction textarea
        const voiceDirInput = page.locator('#audio_instructions');
        await expect(voiceDirInput).toBeVisible();

        // 2. Edit it
        const newInstructions = 'Falar com tom de mistério e suspense.';
        await voiceDirInput.fill(newInstructions);

        // 3. Blur to trigger save and wait for response 
        const putPromise = page.waitForResponse(resp => resp.url().includes('/api/v1/videos/') && resp.request().method() === 'PUT');
        await voiceDirInput.blur();
        const response = await putPromise;
        console.log('PUT Response status:', response.status());
        const respBody = await response.json();
        console.log('PUT Response body:', JSON.stringify(respBody, null, 2));

        // Wait for visual indicator of save if any, or just a small buffer
        await page.waitForTimeout(2000);

        // 4. Reload page to verify persistence
        await page.reload();
        await expect(page.locator('.processing-timeline')).toBeVisible({ timeout: 15000 });
        await expect(voiceDirInput).toHaveValue(newInstructions, { timeout: 10000 });


        // --- Part 2: Scene Narration ---
        // 1. Wait for scenes to be generated/visible
        // This might take time if the backend is doing initial generation (Real AI).
        console.log('Waiting for scenes to be generated...');

        // Check for error modal just in case
        const errorModal = page.locator('.app-modal-visual').filter({ hasText: 'Erro' });
        if (await errorModal.isVisible()) {
            console.log('Error modal visible!');
        }

        // Wait for at least one scene card
        const sceneCard = page.locator('.scene-card').first();
        await expect(sceneCard).toBeVisible({ timeout: 180000 }); // Wait up to 3 mins for generation

        // 2. Locate Narration InlineEditable
        const narrationContainer = sceneCard.locator('.narration-container');
        const inlineEditable = narrationContainer.locator('.inline-editable');

        // 3. Click to edit
        await inlineEditable.click();

        // 4. Type new text
        const newNarration = 'Esta é uma narração editada pelo teste E2E.';
        const textarea = inlineEditable.locator('textarea');
        await expect(textarea).toBeVisible();
        await textarea.fill(newNarration);

        // 5. Save
        await textarea.blur();

        // Wait for saving indicator to disappear
        await expect(inlineEditable.locator('.saving-indicator')).not.toBeVisible();
        await page.waitForTimeout(2000); // Buffer for persistence

        // 6. Verify text in display mode
        await expect(inlineEditable.locator('.text-content')).toContainText(newNarration);

        // 7. Reload and verify
        await page.reload();
        await expect(page.locator('.scene-card').first()).toBeVisible({ timeout: 60000 });
        await expect(page.locator('.scene-card').first().locator('.narration-container .text-content')).toContainText(newNarration);
    });

    test.afterEach(async ({ page }) => {
        const { cleanupTestVideos } = await import('./utils/cleanup');
        await cleanupTestVideos(page);
    });
});
