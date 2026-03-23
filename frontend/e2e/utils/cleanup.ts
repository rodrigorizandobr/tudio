import { Page, expect } from '@playwright/test';

export async function cleanupTestVideos(page: Page) {
    const testTitles = [
        "Teste de edição de vídeo curto (E2E).",
        "Teste E2E Roteiro",
        "Um documentário sobre a história da internet em 30 segundos."
    ];

    console.log('Starting cleanup of test videos...');

    // Ensure we are on the dashboard (exact /panel or /panel/)
    const currentUrl = page.url();
    if (!currentUrl.endsWith('/panel') && !currentUrl.endsWith('/panel/')) {
        await page.goto('/panel');
    }

    // Wait for list to load
    await page.waitForSelector('.video-item', { timeout: 10000 }).catch(() => {
        console.log('No video items found during cleanup');
    });

    let items = page.locator('.video-item');
    let count = await items.count();

    for (let i = 0; i < count; i++) {
        // Re-locate items in case the DOM changed after a deletion
        items = page.locator('.video-item');
        count = await items.count();
        if (i >= count) break;

        const item = items.nth(i);
        const titleElement = item.locator('.video-title');
        const title = await titleElement.innerText().catch(() => '');

        if (testTitles.some(t => title.includes(t))) {
            console.log(`Deleting test video: ${title}`);

            // Hover to reveal actions
            await item.hover();

            const deleteBtn = item.locator('[data-testid="delete-video-btn"]');
            if (await deleteBtn.isVisible()) {
                await deleteBtn.click();
                // Wait for the specific element to go away, much faster than a fixed timeout
                await expect(item).not.toBeVisible({ timeout: 5000 }).catch(() => {
                    console.log('Item still visible or already gone.');
                });
                i--; // Stay at current index for next item
            }
        }
    }

    console.log('Cleanup finished.');
}
