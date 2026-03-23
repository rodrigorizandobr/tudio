import re
from playwright.sync_api import Page, expect

def test_redirect_to_login(page: Page, base_url):
    # 1. Visit Root
    page.goto(base_url)
    
    # 2. Should redirect to /login
    expect(page).to_have_url(re.compile(r".*/login"))
    
    # 3. Check UI elements
    expect(page.get_by_text("TudioV2")).to_be_visible()
    expect(page.get_by_label("Endereço de Email")).to_be_visible()

def test_login_flow(page: Page, base_url):
    page.goto(f"{base_url}/login")
    
    # 1. Fill Form
    page.get_by_label("Endereço de Email").fill("rodrigorizando@gmail.com")
    page.get_by_label("Senha").fill("admin@123") # Using correct password from User Rules
    
    # 2. Submit
    page.get_by_role("button", name="Entrar").click()
    
    # 3. Expect Redirect to /panel
    page.wait_for_url(re.compile(r".*/panel"), timeout=10000)
    expect(page).to_have_url(re.compile(r".*/panel"))
    
    # 4. Check Dashboard visible
    expect(page.get_by_text("Meus Roteiros")).to_be_visible()

def test_login_failure(page: Page, base_url):
    page.goto(f"{base_url}/login")
    
    page.get_by_label("Endereço de Email").fill("wrong@user.com")
    page.get_by_label("Senha").fill("wrongpass")
    
    page.get_by_role("button", name="Entrar").click()
    
    # Check for likely error messages (backend returns "Incorrect email or password")
    # Store maps it to this or shows 'Login failed'
    expect(page.locator(".error-message")).to_be_visible()

def test_logout_flow(page: Page, base_url):
    # Login first
    page.goto(f"{base_url}/login")
    page.get_by_label("Endereço de Email").fill("rodrigorizando@gmail.com")
    page.get_by_label("Senha").fill("admin@123")
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_url(re.compile(r".*/panel"), timeout=10000)
    expect(page).to_have_url(re.compile(r".*/panel"))
    
    # Logout
    # Currently logout is a button in the sidebar footer
    # Using specific selector or role
    page.locator(".logout-btn").click()
    
    # Expect redirect to Login
    expect(page).to_have_url(re.compile(r".*/login"))
