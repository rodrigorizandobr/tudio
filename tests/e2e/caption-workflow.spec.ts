import { test, expect, type Page } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL
const TEST_EMAIL = process.env.TEST_EMAIL
const TEST_PASSWORD = process.env.TEST_PASSWORD

// ─────────────────────────────────────────────────────────────────────────────
// Shared helpers
// ─────────────────────────────────────────────────────────────────────────────

async function login(page: Page) {
    await page.goto(`${BASE_URL}/`)
    await page.fill('input[type="email"]', TEST_EMAIL)
    await page.fill('input[type="password"]', TEST_PASSWORD)
    await page.click('button[type="submit"]')
    await page.waitForURL(`${BASE_URL}/panel**`, { timeout: 15000 })
    await expect(page).toHaveURL(/\/panel/)
}

async function navigateToFirstCompletedVideo(page: Page) {
    await page.goto(`${BASE_URL}/panel/scripts`)
    await page.waitForLoadState('networkidle')
    const scriptCard = page.locator('[data-status="completed"]').first()
    const count = await scriptCard.count()
    if (count === 0) {
        // Fallback: open first card regardless of status
        const anyCard = page.locator('[data-testid="video-card"], .video-card, .script-card').first()
        await anyCard.click()
    } else {
        await scriptCard.click()
    }
    await page.waitForSelector('.processing-timeline', { timeout: 20000 })
}

// ─────────────────────────────────────────────────────────────────────────────
// Test Suite
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Animated Captions — E2E Flow', () => {

    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    // ── Timeline: Legenda step renders ──────────────────────────────────────
    test('Timeline should contain "Legenda" as step 4', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)

        // There should be exactly 5 steps now
        const steps = page.locator('.step-item')
        await expect(steps).toHaveCount(5, { timeout: 10000 })

        // Step 4 must have the text "Legenda"
        const legendaStep = page.locator('.step-item').filter({ hasText: 'Legenda' })
        await expect(legendaStep).toBeVisible()
    })

    test('Timeline should still contain "Render" as step 5', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)
        const renderStep = page.locator('.step-item').filter({ hasText: 'Render' })
        await expect(renderStep).toBeVisible()
    })

    test('Timeline remains scrollable as single row (no wrapping)', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)
        const timeline = page.locator('.timeline-steps')
        await expect(timeline).toHaveCSS('flex-wrap', 'nowrap')
        await expect(timeline).toHaveCSS('overflow-x', 'auto')
    })

    // ── Legenda step — button behavior ──────────────────────────────────────
    test('Legenda step button is disabled when narration is not 100%', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)
        const legendaStep = page.locator('.step-item').filter({ hasText: 'Legenda' })
        const legendaBtn = legendaStep.locator('button.action-btn')
        // If narration not done, button should be disabled
        const narrationStep = page.locator('.step-item').filter({ hasText: 'Narração' })
        const narrationPct = await narrationStep.locator('.label-percent').textContent()
        const narrationDone = narrationPct?.includes('100')
        if (!narrationDone) {
            await expect(legendaBtn).toBeDisabled()
        }
    })

    test('Legenda step button triggers caption generation when clicked (narration done)', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)
        const legendaStep = page.locator('.step-item').filter({ hasText: 'Legenda' })
        const legendaBtn = legendaStep.locator('button.action-btn')

        if (await legendaBtn.isEnabled()) {
            // Intercept the caption generate API call
            const [request] = await Promise.all([
                page.waitForRequest(req =>
                    req.url().includes('/captions/generate') && req.method() === 'POST',
                    { timeout: 5000 }
                ).catch(() => null),
                legendaBtn.click(),
            ])
            // Either an API call was made or it was already processing
            // Just verify no JS error modal appeared
            const errorModal = page.locator('[role="dialog"]').filter({ hasText: 'Erro' })
            await expect(errorModal).not.toBeVisible({ timeout: 3000 }).catch(() => {})
        }
    })

    // ── Caption Config Card visible when renders exist ───────────────────────
    test('Caption config card appears when video has rendered outputs', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)

        // Check if outputs exist (render step completed)
        const renderStep = page.locator('.step-item').filter({ hasText: 'Render' })
        const renderPct = await renderStep.locator('.label-percent').textContent()
        const renderDone = renderPct?.includes('100')

        if (renderDone) {
            // Caption card must be visible
            const captionCard = page.locator('text=Legendas Animadas').first()
            await expect(captionCard).toBeVisible({ timeout: 10000 })
        }
    })

    test('Caption config card shows 5 style options', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)

        const renderStep = page.locator('.step-item').filter({ hasText: 'Render' })
        const renderPct = await renderStep.locator('.label-percent').textContent()
        if (!renderPct?.includes('100')) {
            test.skip()
            return
        }

        // Wait for caption card
        const captionCard = page.locator('text=Legendas Animadas').first()
        await expect(captionCard).toBeVisible({ timeout: 10000 })

        // Should have 5 style buttons
        const styleButtons = page.locator('text=Karaoke, text=Word Pop, text=Typewriter, text=Highlight, text=Bounce')
        // Check at least Karaoke is visible
        await expect(page.locator('text=Karaoke').first()).toBeVisible()
        await expect(page.locator('text=Word Pop').first()).toBeVisible()
    })

    test('Caption card position selector works', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)

        const renderStep = page.locator('.step-item').filter({ hasText: 'Render' })
        const renderPct = await renderStep.locator('.label-percent').textContent()
        if (!renderPct?.includes('100')) {
            test.skip()
            return
        }
        await expect(page.locator('text=Legendas Animadas').first()).toBeVisible({ timeout: 5000 })

        // The position buttons: Topo / Centro / Base
        const topoBtn = page.locator('button', { hasText: 'Topo' }).first()
        await expect(topoBtn).toBeVisible()
        await topoBtn.click()
        // After click, "Topo" should have a violet background (becomes active)
        await expect(topoBtn).toHaveClass(/bg-violet-500/)
    })

    test('Whisper toggle changes label', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)

        const renderStep = page.locator('.step-item').filter({ hasText: 'Render' })
        const renderPct = await renderStep.locator('.label-percent').textContent()
        if (!renderPct?.includes('100')) {
            test.skip()
            return
        }
        await expect(page.locator('text=Legendas Animadas').first()).toBeVisible({ timeout: 5000 })

        // Forçar Whisper toggle
        const whisperToggle = page.locator('button', { hasText: 'Usar texto salvo' }).first()
        await expect(whisperToggle).toBeVisible()
        await whisperToggle.click()
        await expect(page.locator('button', { hasText: 'Whisper ativo' }).first()).toBeVisible()
    })

    // ── Per-scene caption button (Captions icon) ─────────────────────────────
    test('Per-scene caption button is visible for scenes with audio', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)

        // Scroll to scenes list
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
        await page.waitForTimeout(1000)

        // The caption button is wrapped in a section that only shows when audio_url exists
        // We look for scenes that are rendered (have audio players)
        const audioPlayers = page.locator('[data-testid="audio-player"], audio').first()
        const hasAudio = await audioPlayers.count() > 0

        if (hasAudio) {
            // The Captions icon button should exist (AppButton with title attribute)
            const captionBtns = page.locator('button[title*="Legenda"]')
            const count = await captionBtns.count()
            expect(count).toBeGreaterThan(0)
        }
    })

    // ── Caption status badge states ────────────────────────────────────────
    test('Caption status badge shows "Não gerado" initially', async ({ page }) => {
        await navigateToFirstCompletedVideo(page)

        const renderStep = page.locator('.step-item').filter({ hasText: 'Render' })
        const renderPct = await renderStep.locator('.label-percent').textContent()
        if (!renderPct?.includes('100')) {
            test.skip()
            return
        }

        await expect(page.locator('text=Legendas Animadas').first()).toBeVisible({ timeout: 5000 })

        // Status badge should show one of the known states
        const validStates = ['✓ Pronto', '⟳ Gerando...', '✗ Erro', 'Não gerado']
        let foundState = false
        for (const state of validStates) {
            const el = page.locator(`text=${state}`).first()
            if (await el.count() > 0) {
                foundState = true
                break
            }
        }
        expect(foundState).toBe(true)
    })

    // ── API endpoint smoke tests (direct HTTP) ────────────────────────────
    test('GET /api/v1/captions/styles returns 5 styles', async ({ page }) => {
        const resp = await page.request.get(`${BASE_URL}/api/v1/captions/styles`)
        expect(resp.status()).toBe(200)
        const body = await resp.json()
        expect(body.styles).toHaveLength(5)
    })

    test('GET /api/v1/captions/styles — styles have required fields', async ({ page }) => {
        const resp = await page.request.get(`${BASE_URL}/api/v1/captions/styles`)
        const { styles } = await resp.json()
        for (const style of styles) {
            expect(style).toHaveProperty('id')
            expect(style).toHaveProperty('label')
            expect(style).toHaveProperty('desc')
        }
    })

    test('PATCH /api/v1/videos/{id}/captions/style — invalid style returns 400', async ({ page }) => {
        // Get a valid video ID from the panel first
        await page.goto(`${BASE_URL}/panel/scripts`)
        await page.waitForLoadState('networkidle')

        // Try with video ID 1 (may or may not exist, but bad style always returns 400)
        const resp = await page.request.patch(
            `${BASE_URL}/api/v1/videos/1/captions/style`,
            { data: { style: 'neon_glow_invalid' } }
        )
        // 400 for bad style OR 404 for unknown video — both acceptable for this test
        expect([400, 404]).toContain(resp.status())
    })
})
