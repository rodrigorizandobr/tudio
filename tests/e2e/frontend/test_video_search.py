import re
import pytest
from playwright.sync_api import Page, expect

def login(page, base_url):
    """Helper function to log in"""
    page.goto(f"{base_url}/login")
    page.get_by_label("Endereço de Email").fill("rodrigorizando@gmail.com")
    page.get_by_label("Senha").fill("admin@123")
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_url(re.compile(r".*/panel"), timeout=10000)
    expect(page).to_have_url(re.compile(r".*/panel"))

def test_video_search_modal_opens(page: Page, base_url):
    """Test that video search modal opens from scene details"""
    login(page, base_url)
    
    # Navigate to scripts
    page.goto(f"{base_url}/panel")
    
    # For this test to work, we need at least one script with scenes
    # We'll assume a script exists from previous tests or seed data
    # Find and click first script
    first_script = page.locator(".script-card").first
    if first_script.is_visible():
        first_script.click()
        
        # Wait for script details page
        page.wait_for_url(re.compile(r".*/panel/scripts/.+"), timeout=10000)
        
        # Find the first scene and click to expand
        first_scene = page.locator(".scene-card").first
        if first_scene.is_visible():
            first_scene.click()
            
            # TODO: Add button to open Video Search Modal
            # For now, this test documents the expected behavior
            pass

@pytest.mark.skip(reason="Waiting for VideoSearchModal integration in VideoDetailsView")
def test_pexels_video_search_flow(page: Page, base_url):
    """Test complete Pexels video search flow"""
    login(page, base_url)
    
    # 1. Navigate to a scene
    page.goto(f"{base_url}/panel")
    first_script = page.locator(".script-card").first
    first_script.click()
    page.wait_for_url(re.compile(r".*/panel/scripts/.+"))
    
    # 2. Click "Buscar Vídeo" button
    page.get_by_title("Buscar Vídeo").click()
    
    # 3. Modal should open
    expect(page.get_by_text("Buscar Vídeo")).to_be_visible()
    
    # 4. Pexels tab should be active by default
    pexels_tab = page.locator("button", has_text="Pexels")
    expect(pexels_tab).to_have_class(re.compile(r"active"))
    
    # 5. Enter search query
    search_input = page.locator("input[placeholder='Digite o termo de busca...']")
    search_input.fill("nature")
    
    # 6. Click search button
    page.get_by_title("Buscar").click()
    
    # 7. Wait for results
    page.wait_for_selector(".video-card", timeout=15000)
    
    # 8. Verify results are displayed
    video_cards = page.locator(".video-card")
    expect(video_cards.first).to_be_visible()
    
    # 9. Click on first video to select
    video_cards.first.click()
    
    # 10. Modal should close
    expect(page.get_by_text("Buscar Vídeo")).not_to_be_visible()
    
    # 11. Video should be assigned to scene
    # TODO: Verify video was saved to scene

@pytest.mark.skip(reason="Waiting for API key configuration")  
def test_pexels_search_with_filters(page: Page, base_url):
    """Test Pexels video search with orientation and quality filters"""
    login(page, base_url)
    
    # Open video search modal (assuming button exists)
    page.get_by_title("Buscar Vídeo").click()
    
    # Change orientation to portrait
    orientation_select = page.locator("select").filter(has_text="Paisagem")
    orientation_select.select_option("portrait")
    
    # Change quality to high
    quality_select = page.locator("select").filter(has_text="Média Qualidade")
    quality_select.select_option("large")
    
    # Search
    page.locator("input[placeholder='Digite o termo de busca...']").fill("mountains")
    page.get_by_title("Buscar").click()
    
    # Wait for results
    page.wait_for_selector(".video-card", timeout=15000)
    
    # Verify results exist
    expect(page.locator(".video-card").first).to_be_visible()

@pytest.mark.skip(reason="Waiting for API key configuration")
def test_pexels_empty_search_results(page: Page, base_url):
    """Test Pexels search with no results"""
    login(page, base_url)
    
    # Open video search modal
    page.get_by_title("Buscar Vídeo").click()
    
    # Search for something that won't return results
    page.locator("input[placeholder='Digite o termo de busca...']").fill("xyzabc123nonexistent")
    page.get_by_title("Buscar").click()
    
    # Wait and verify empty state
    expect(page.get_by_text('Nenhum vídeo encontrado para "xyzabc123nonexistent"')).to_be_visible(timeout=15000)

@pytest.mark.skip(reason="Waiting for API key configuration")
def test_pexels_provider_tab_selection(page: Page, base_url):
    """Test switching between provider tabs"""
    login(page, base_url)
    
    # Open video search modal
    page.get_by_title("Buscar Vídeo").click()
    
    # Verify Pexels is active
    pexels_tab = page.locator("button", has_text="Pexels")
    expect(pexels_tab).to_have_class(re.compile(r"active"))
    
    # Try to click Pixabay (should be enabled)
    pixabay_tab = page.locator("button", has_text="Pixabay")
    expect(pixabay_tab).to_be_enabled()
    pixabay_tab.click()
    expect(pixabay_tab).to_have_class(re.compile(r"active"))
    
    # Try to click Google (should be disabled)
    google_tab = page.locator("button", has_text="Google")
    expect(google_tab).to_be_disabled()


def test_pixabay_search_flow(page: Page, base_url):
    """Test complete Pixabay search and application flow"""
    login(page, base_url)
    
    # 1. Navigate to a scene
    page.goto(f"{base_url}/panel")
    first_script = page.locator(".script-card").first
    first_script.click()
    page.wait_for_url(re.compile(r".*/panel/scripts/.+"))
    
    # 2. Open Video Search Modal
    page.get_by_title("Buscar Vídeo").click()
    expect(page.get_by_text("Buscar Vídeo")).to_be_visible()
    
    # 3. Select Pixabay
    page.locator("button", has_text="Pixabay").click()
    
    # 4. Search for "sunset"
    page.locator("input[placeholder='Digite o termo de busca...']").fill("sunset")
    page.get_by_title("Buscar").click()
    
    # 5. Wait for results
    page.wait_for_selector(".video-card", timeout=15000)
    
    # 6. Verify results
    results = page.locator(".video-card")
    expect(results.first).to_be_visible()
    
    # 7. Select video
    results.first.click()
    
    # 8. Verify modal closes
    expect(page.get_by_text("Buscar Vídeo")).not_to_be_visible()

def test_video_search_modal_closes(page: Page, base_url):
    """Test that video search modal closes properly"""
    login(page, base_url)
    
    # TODO: Implement after VideoSearchModal integration
    # Open modal -> Close via X button or cancel
    pass
