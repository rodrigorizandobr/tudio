import re
from playwright.sync_api import Page, expect

def login(page, base_url):
    page.goto(f"{base_url}/login")
    page.get_by_label("Endereço de Email").fill("rodrigorizando@gmail.com")
    page.get_by_label("Senha").fill("admin@123")
    page.get_by_role("button", name="Entrar").click()
    # Wait for navigation to complete
    page.wait_for_url(re.compile(r".*/panel"), timeout=10000)
    expect(page).to_have_url(re.compile(r".*/panel"))

def test_create_script_wizard(page: Page, base_url):
    login(page, base_url)
    
    # 1. Click New Script (Icon button) -- might need a better selector if no text
    # The button has title="Novo Roteiro"
    page.get_by_title("Novo Roteiro").click()
    
    # 2. Check Wizard URL
    expect(page).to_have_url(re.compile(r".*/panel/scripts/new"))
    expect(page.get_by_text("Criar Novo Roteiro")).to_be_visible()
    
    # 3. Fill Form
    page.get_by_label("Sobre o que é o seu vídeo?").fill("Frontend E2E Test Script")
    page.get_by_label("Duração Alvo").fill("3")
    # Language default is pt-br
    
    # 4. Submit
    # Button is now Icon-only with title "Gerar Roteiro"
    page.get_by_role("button", name="Gerar Roteiro").click()
    
    # 5. Expect redirect to details
    # URL should look like /panel/scripts/UUID
    expect(page).to_have_url(re.compile(r".*/panel/scripts/.+"))
    
    # 6. Verify Status Processing
    # Depending on speed, it might be processing or completed (if mocked internally)
    # The status box should be visible
    expect(page.locator(".status-box")).to_be_visible()
    expect(page.get_by_text("Frontend E2E Test Script")).to_be_visible()

def test_script_list_navigation(page: Page, base_url):
    login(page, base_url)
    
    # Check if we are on list
    expect(page).to_have_url(re.compile(r".*/panel"))
    
    # If we just created a script, it should be in the list
    # Because persistence is file-based (or mock datastore in tests?), it depends on the server environment.
    # Our conftest.py launches the REAL app with settings loaded.
    # If using local file storage, it will persist to `storage/data` or `storage/data_test` if configured.
    # We should see the script we just created if execution order allows.
    
    expect(page.get_by_text("Meus Roteiros")).to_be_visible()
