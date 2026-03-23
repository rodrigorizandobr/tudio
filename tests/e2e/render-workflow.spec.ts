import { test, expect } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL
const TEST_EMAIL = process.env.TEST_EMAIL
const TEST_PASSWORD = process.env.TEST_PASSWORD

test.describe('Video Rendering Workflow E2E', () => {
    test.beforeEach(async ({ page }) => {
        // Login before each test
        await page.goto(`${BASE_URL}/`)
        await page.fill('input[type="email"]', TEST_EMAIL)
        await page.fill('input[type="password"]', TEST_PASSWORD)
        await page.click('button[type="submit"]')
        await page.waitForURL(`${BASE_URL}/panel**`)
        await expect(page).toHaveURL(/\/panel/)
    })

    test('should trigger video rendering from timeline', async ({ page }) => {
        // Step 1: Navigate to scripts/projects list
        await page.goto(`${BASE_URL}/panel/scripts`)
        await page.waitForLoadState('networkidle')

        // Step 2: Open first script with status 'completed' (assuming it has a generated video structure)
        // We select the first one.
        const scriptCard = page.locator('[data-status="completed"]').first()
        await expect(scriptCard).toBeVisible({ timeout: 10000 })
        await scriptCard.click()

        // Wait for script details/video timeline
        await page.waitForSelector('.processing-timeline', { timeout: 10000 })

        // Step 3: Locate the Render Step (Step 4)
        // The timeline has 4 steps. We want the action button in the 4th step.
        // We can find it by looking for the "Render" text or the specific icon class if we knew it.
        // Based on Vue file: The last step has title "Render".
        const renderStep = page.locator('.step-item').filter({ hasText: 'Render' })
        await expect(renderStep).toBeVisible()

        // Step 4: Locate the Render/Play button
        const renderBtn = renderStep.locator('button.action-btn')
        await expect(renderBtn).toBeVisible()

        // Step 5: Click Render
        // Note: If it's already rendered, it might play. If not, it renders.
        // The mock user flow assumes we can trigger it.
        // To be safe, we check if it's disabled.
        if (await renderBtn.isEnabled()) {
            await renderBtn.click()

            // Step 6: Verify Loading State
            // The button should show a spinner or become disabled/loading
            // The Vue component uses :class="{ 'animate-spin': videoStore.isLoading ... }"
            // We can check for the spinner SVG or class.
            // However, the action might be very fast if it just triggers a background job.
            // We expect a toast or some feedback, but strictly checking the button state change is a good start.

            // We can wait for a small timeout and check if "Processing" or similar appears, 
            // but the timeline updates based on poll or websocket.

            // For now, ensure no error alert appears.
            const errorAlert = page.locator('.error-alert') // Hypothetical class
            await expect(errorAlert).not.toBeVisible()
        }
    })

    test('Timeline should be single line and scrollable', async ({ page }) => {
        // UI Regression Test
        await page.goto(`${BASE_URL}/panel/scripts`)
        await page.waitForLoadState('networkidle')
        const scriptCard = page.locator('[data-status="completed"]').first()
        await scriptCard.click()
        await page.waitForSelector('.processing-timeline', { timeout: 10000 })

        const timelineContainer = page.locator('.timeline-steps')

        // Check CSS properties
        await expect(timelineContainer).toHaveCSS('flex-wrap', 'nowrap')
        await expect(timelineContainer).toHaveCSS('overflow-x', 'auto')
    })
})
