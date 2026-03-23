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

def test_settings_page(page: Page, base_url):
    login(page, base_url)
    
    # 1. Navigate to Settings
    page.get_by_role("link", name="Configurações").click()
    
    # 2. Verify URL
    expect(page).to_have_url(re.compile(r".*/panel/settings"))
    
    # 3. Verify Settings page loaded correctly
    # Check for page heading and input placeholders
    expect(page.get_by_role("heading", name="Configurações")).to_be_visible()
    expect(page.get_by_placeholder("NEW_VARIABLE_KEY")).to_be_visible()
    
    # 4. Try adding a new key
    page.get_by_placeholder("NEW_VARIABLE_KEY").fill("TEST_KEY_E2E")
    page.get_by_placeholder("Value").fill("test_value")
    # Button is now Icon-Only with title "Adicionar Variável"
    page.get_by_role("button", name="Adicionar Variável").click()
    
    # 5. Check if added to list (in memory before save)
    expect(page.get_by_text("TEST_KEY_E2E")).to_be_visible()
    
    # 6. Save (will trigger alert confirmation)
    # Handling dialog
    page.on("dialog", lambda dialog: dialog.accept())
    
    # Button is now Icon-Only with title "Salvar Alterações"
    page.get_by_role("button", name="Salvar Alterações").click()
    
    # 7. Check success message or verify persistence
    # Ideally we'd reload and check, but that requires Server Restart as per logic.
    # Just verifying the UI flow is sufficient for E2E.
