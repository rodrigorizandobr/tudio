import { test, expect } from '@playwright/test'

/**
 * E2E Tests for Image Search, Download, and Crop Workflow
 * Sprint 42-44 Image Processing Pipeline
 */

// Test configuration
const BASE_URL = process.env.E2E_BASE_URL
const TEST_EMAIL = process.env.TEST_EMAIL
const TEST_PASSWORD = process.env.TEST_PASSWORD

test.describe('Image Workflow E2E', () => {
    test.beforeEach(async ({ page }) => {
        // Login before each test
        await page.goto(`${BASE_URL}/`)

        // Fill login form
        await page.fill('input[type="email"]', TEST_EMAIL)
        await page.fill('input[type="password"]', TEST_PASSWORD)

        // Submit and wait for navigation
        await page.click('button[type="submit"]')
        await page.waitForURL(`${BASE_URL}/panel**`)

        // Verify we're logged in
        await expect(page).toHaveURL(/\/panel/)
    })

    test('should complete full image search and download workflow', async ({ page }) => {
        // Step 1: Navigate to scripts list
        await page.goto(`${BASE_URL}/panel/scripts`)
        await page.waitForLoadState('networkidle')

        // Step 2: Open first script with status 'completed'
        const scriptCard = page.locator('[data-status="completed"]').first()
        await expect(scriptCard).toBeVisible({ timeout: 10000 })
        await scriptCard.click()

        // Wait for script details
        await page.waitForSelector('.scene-card', { timeout: 10000 })

        // Step 3: Find a scene with image_search field
        const imageSearchButton = page.locator('button[title*="Buscar"]').first()
        await expect(imageSearchButton).toBeVisible()
        await imageSearchButton.click()

        // Step 4: Image search modal should open
        await page.waitForSelector('.image-search-modal', { timeout: 5000 })
        const modal = page.locator('.image-search-modal')
        await expect(modal).toBeVisible()

        // Step 5: Perform search
        const searchInput = modal.locator('input[type="text"]')
        await searchInput.fill('nature')
        await searchInput.press('Enter')

        // Wait for search results
        await page.waitForSelector('.image-result', { timeout: 10000 })

        // Step 6: Select first image
        const firstImage = page.locator('.image-result').first()
        await expect(firstImage).toBeVisible()
        await firstImage.click()

        // Step 7: Verify image was downloaded and modal closed
        await expect(modal).not.toBeVisible({ timeout: 5000 })

        // Step 8: Verify image appears in scene card
        const sceneImage = page.locator('.scene-image-preview img').first()
        await expect(sceneImage).toBeVisible({ timeout: 10000 })

        // Verify image src contains storage path
        const imageSrc = await sceneImage.getAttribute('src')
        expect(imageSrc).toContain('/api/storage/images/')

        // Verify "Imagem Selecionada" label
        const imageLabel = page.locator('.image-label').first()
        await expect(imageLabel).toHaveText('Imagem Selecionada')
    })

    test('should complete image crop workflow', async ({ page }) => {
        // Navigate to script with downloaded image
        await page.goto(`${BASE_URL}/panel/scripts`)
        await page.waitForLoadState('networkidle')

        const scriptCard = page.locator('[data-status="completed"]').first()
        await scriptCard.click()
        await page.waitForSelector('.scene-card')

        // Find scene with downloaded image
        const cropButton = page.locator('button.crop-btn').first()

        // If no crop button exists, skip this test
        if (!(await cropButton.isVisible())) {
            test.skip()
            return
        }

        // Click crop button
        await cropButton.click()

        // Crop editor modal should open
        await page.waitForSelector('.crop-editor', { timeout: 5000 })
        const cropModal = page.locator('.crop-editor')
        await expect(cropModal).toBeVisible()

        // Select aspect ratio
        const ratio16x9 = cropModal.locator('button').filter({ hasText: '16:9' })
        await ratio16x9.click()
        await expect(ratio16x9).toHaveClass(/active/)

        // Wait for cropper to load
        await page.waitForTimeout(1000)

        // Save crop
        const saveCropButton = cropModal.locator('button').filter({ hasText: 'Salvar Crop' })
        await saveCropButton.click()

        // Modal should close
        await expect(cropModal).not.toBeVisible({ timeout: 5000 })

        // Verify cropped image appears
        const croppedImage = page.locator('.scene-image-preview.cropped img').first()
        await expect(croppedImage).toBeVisible({ timeout: 10000 })

        // Verify cropped label
        const croppedLabel = page.locator('.image-label.cropped').first()
        await expect(croppedLabel).toHaveText('Cortada')
    })

    test('should handle API errors gracefully', async ({ page }) => {
        // Navigate to scripts
        await page.goto(`${BASE_URL}/panel/scripts`)
        await page.waitForLoadState('networkidle')

        const scriptCard = page.locator('[data-status="completed"]').first()
        await scriptCard.click()
        await page.waitForSelector('.scene-card')

        // Open image search
        const searchButton = page.locator('button[title*="Buscar"]').first()

        if (!(await searchButton.isVisible())) {
            test.skip()
            return
        }

        await searchButton.click()

        // Wait for modal
        const modal = page.locator('.image-search-modal')
        await expect(modal).toBeVisible()

        // Search for something that might fail
        const searchInput = modal.locator('input[type="text"]')
        await searchInput.fill('xyzinvalidquery123')
        await searchInput.press('Enter')

        // Should show results (even if empty) or error message
        // Not fail catastrophically
        await page.waitForTimeout(2000)

        // Verify modal still functional
        await expect(modal).toBeVisible()

        // Close modal
        const closeButton = modal.locator('button').filter({ hasText: 'Cancelar' }).or(modal.locator('button[title="Fechar"]'))
        if (await closeButton.isVisible()) {
            await closeButton.click()
        }
    })
})

test.describe('Image API Integration', () => {
    test('GET /api/v1/images/search should return results', async ({ request }) => {
        // Login first to get token
        const loginResponse = await request.post(`${BASE_URL}/api/v1/auth/login`, {
            data: {
                email: TEST_EMAIL,
                password: TEST_PASSWORD
            }
        })

        expect(loginResponse.ok()).toBeTruthy()
        const { access_token } = await loginResponse.json()

        // Search images
        const searchResponse = await request.get(`${BASE_URL}/api/v1/images/search`, {
            headers: {
                'Authorization': `Bearer ${access_token}`
            },
            params: {
                q: 'ocean',
                limit: 10
            }
        })

        expect(searchResponse.ok()).toBeTruthy()
        const results = await searchResponse.json()

        // Verify structure
        expect(Array.isArray(results)).toBeTruthy()
        if (results.length > 0) {
            expect(results[0]).toHaveProperty('id')
            expect(results[0]).toHaveProperty('url')
            expect(results[0]).toHaveProperty('thumb')
        }
    })

    test('POST /api/v1/images/download should download and store image', async ({ request }) => {
        // Login
        const loginResponse = await request.post(`${BASE_URL}/api/v1/auth/login`, {
            data: {
                email: TEST_EMAIL,
                password: TEST_PASSWORD
            }
        })

        const { access_token } = await loginResponse.json()

        // Download image
        const downloadResponse = await request.post(`${BASE_URL}/api/v1/images/download`, {
            headers: {
                'Authorization': `Bearer ${access_token}`
            },
            data: {
                image_url: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4',
                script_id: 999999,
                scene_id: 'test-1-1-1'
            }
        })

        expect(downloadResponse.ok()).toBeTruthy()
        const result = await downloadResponse.json()

        expect(result).toHaveProperty('original_image_url')
        expect(result.original_image_url).toContain('images/')
    })

    test('PUT /api/v1/scripts/{id} should update script data', async ({ request }) => {
        // Login
        const loginResponse = await request.post(`${BASE_URL}/api/v1/auth/login`, {
            data: {
                email: TEST_EMAIL,
                password: TEST_PASSWORD
            }
        })

        const { access_token } = await loginResponse.json()

        // Get existing script
        const scriptsResponse = await request.get(`${BASE_URL}/api/v1/scripts/`, {
            headers: {
                'Authorization': `Bearer ${access_token}`
            }
        })

        const scripts = await scriptsResponse.json()
        if (scripts.length === 0) {
            test.skip()
            return
        }

        const scriptId = scripts[0].id

        // Update script
        const updateResponse = await request.put(`${BASE_URL}/api/v1/scripts/${scriptId}`, {
            headers: {
                'Authorization': `Bearer ${access_token}`
            },
            data: scripts[0] // Send same data back
        })

        expect(updateResponse.ok()).toBeTruthy()
        const updated = await updateResponse.json()
        expect(updated).toHaveProperty('id')
        expect(updated.id).toBe(scriptId)
    })
})
