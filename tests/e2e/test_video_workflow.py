import pytest
from playwright.sync_api import Page, expect
import re

import os

BASE_URL = os.environ["E2E_BASE_URL"]
TEST_EMAIL = os.environ["TEST_EMAIL"]
TEST_PASSWORD = os.environ["TEST_PASSWORD"]

def test_video_search_and_playback(page: Page):
    # 1. Login
    page.goto(f"{BASE_URL}/")
    
    # Check if already logged in or need login
    if page.url.endswith("/panel"):
        pass
    else:
        page.fill('input[type="email"]', TEST_EMAIL)
        page.fill('input[type="password"]', TEST_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url(f"{BASE_URL}/panel**")

    # 2. Go to videos
    page.goto(f"{BASE_URL}/panel/videos")
    
    # 3. Open a video
    # Wait for video items
    page.wait_for_selector('.video-item', timeout=10000)
    video_item = page.locator('.video-item').first
    video_item.click()
    
    # 4. Wait for scene details
    page.wait_for_selector('.scene-card', timeout=10000)
    
    # 5. Open Video Search Modal
    # Look for the button with title "Buscar Vídeo" inside the FIRST scene card
    scene_card = page.locator('.scene-card').first
    search_btn = scene_card.locator('button[title*="Vídeo"]') # Title might simply be "Buscar Vídeo" or icon
    # Just in case, try to find by specific class or icon if title fails, but sticking to title for now.
    # The artifact image shows a button with a video icon.
    if not search_btn.is_visible():
         # Maybe it's solely icon based? Try filtering by icon class or role
         search_btn = scene_card.locator('button').filter(has_text="Vídeo").first
         if not search_btn.is_visible():
             # Fallback: look for the button next to others
              pass

    search_btn.click()
    
    # 6. Modal interaction
    # VideoSearchModal.vue uses AppModal -> standard modal selectors
    # Wait for modal to appear
    page.wait_for_selector('.search-modal', timeout=5000)
    
    # Switch to Google Provider
    page.click('button[title="Busca via SerpApi"]')
    
    # 7. Search "nature"
    input_field = page.locator('input[placeholder*="Digite o termo"]')
    input_field.fill("nature")
    input_field.press("Enter")
    
    # 8. Wait for results
    page.wait_for_selector('.video-card', timeout=20000) # Increased timeout for search
    
    # 9. Select a video by clicking the card (this closes modal and triggers download in VideoDetailsView)
    # This matches user behavior: "cliquei no primeiro vídeo... a modal fecha"
    page.locator('.video-card').first.click()
    
    # 10. Wait for modal close
    expect(page.locator('.search-modal')).not_to_be_visible(timeout=5000)
    
    # 11. Verify Player
    # Initially it might show optimistic URL (external), then switch to local.
    # We want to verify it eventually becomes playable local file.
    video_container = scene_card.locator('.scene-video-container')
    expect(video_container).to_be_visible(timeout=10000)
    
    video_el = video_container.locator('video')
    expect(video_el).to_be_visible()
    
    # Wait for src to be a local path (containing 'storage' or 'api') and NOT external
    # Because user issue was about the downloaded file valid path.
    # Note: Optimization logic in frontend sets it to external temporarily.
    # We wait for the download to finish (backend call in frontend).
    # Since we can't easily wait for API response in playwright without intercept,
    # we'll wait for the attribute to be updated.
    
    # Wait for src to be a local path (containing 'storage' or 'api') and NOT external
    # Note: Vue renders <source> inside <video>
    source_el = video_el.locator('source')
    expect(source_el).to_have_attribute("src", re.compile(r".*storage/.*"), timeout=60000)
    
    # Check if src is correct (no double storage)
    src = source_el.get_attribute("src")
    print(f"Final Video SRC: {src}")
    
    assert "/storage/storage/" not in src, "Found double storage path in URL"
    assert "storage/videos/google" in src or "storage/videos" in src, "Path should be in storage"
