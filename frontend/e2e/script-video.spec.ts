import { test, expect } from '@playwright/test';

test.describe('Script to Video Wizard', () => {
    test('should toggle script mode and allow script submission', async ({ page }) => {
        // 1. Login
        console.log('--- Step 1: Login ---');
        await page.goto('/login');
        await page.fill('input[type="email"]', 'rodrigorizando@gmail.com');
        await page.fill('input[type="password"]', 'admin@123');
        await page.click('[data-testid="btn-login"]');

        // Wait for dashboard
        await expect(page.locator('.app-sidebar')).toBeVisible({ timeout: 60000 });

        console.log('--- Step 2: Navigate to Video Create ---');
        // Correct path according to router/index.ts: /panel/videos/new
        await page.goto('/panel/videos/new');

        // Wait for the wizard card to ensure component is loaded
        console.log('Waiting for wizard card...');
        await page.waitForSelector('.wizard-container', { timeout: 30000 }); // Correct class

        // 3. Verify "Tenho um Roteiro" button exists and click it
        console.log('Checking for "Tenho um Roteiro" button...');
        // Look for the specific button. It might be a button with text or specific class.
        // Assuming it is one of the toggle buttons.
        const scriptModeBtn = page.locator('button', { hasText: 'Tenho um Roteiro' });
        await expect(scriptModeBtn).toBeVisible();
        await scriptModeBtn.click();

        // 4. Verify Textarea appears
        console.log('Checking for Script Textarea...');
        const scriptInput = page.locator('textarea#script'); // Correct ID
        await expect(scriptInput).toBeVisible();

        // 5. Fill Script
        console.log('Filling script...');
        // Need to fill topic/title first as it is required
        await page.fill('#topic', 'Teste E2E Roteiro');

        await scriptInput.fill(`
        Cena 1
        Narrador: Bem-vindo ao tutorial.
        Visual: Um logo aparece na tela.
        
        Cena 2
        Narrador: Vamos aprender sobre automação.
        Visual: Um robô digitando no computador.
        `);

        // 6. Submit
        console.log('Clicking Submit...');
        const submitBtn = page.locator('button', { hasText: 'Gerar Vídeo' });
        await submitBtn.click();

        // 7. Verify Redirection
        console.log('Waiting for redirection to Video Details...');
        // Should redirect to /panel/videos/{id}
        await expect(page).toHaveURL(/\/panel\/videos\/\d+/, { timeout: 30000 });
        expect(page.url()).toContain('/panel/videos/');
        console.log('Success!');
    });

    test.afterEach(async ({ page }) => {
        const { cleanupTestVideos } = await import('./utils/cleanup');
        await cleanupTestVideos(page);
    });
});
