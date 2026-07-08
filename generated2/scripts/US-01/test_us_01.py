import pytest
from pages import LoginPage, RequestsPage

def test_tc_01_01_login_sucesso(driver, credentials_valid):
    login_page = LoginPage(driver)
    requests_page = RequestsPage(driver)
    
    login_page.navigate()
    login_page.login(credentials_valid["email"], credentials_valid["password"])
    
    assert requests_page.is_table_visible()
    assert "/requests" in driver.current_url

def test_tc_01_02_senha_incorreta(driver, credentials_invalid_pass):
    login_page = LoginPage(driver)
    
    login_page.navigate()
    login_page.login(credentials_invalid_pass["email"], credentials_invalid_pass["password"])
    
    assert login_page.get_error_message() == "E-mail ou senha inválidos."
    assert login_page.is_on_page()

def test_tc_01_03_email_inexistente(driver, credentials_nonexistent):
    login_page = LoginPage(driver)
    
    login_page.navigate()
    login_page.login(credentials_nonexistent["email"], credentials_nonexistent["password"])
    
    assert login_page.get_error_message() == "E-mail ou senha inválidos."
    assert login_page.is_on_page()

def test_tc_01_04_lockout_seis_tentativas(driver, credentials_lockout):
    login_page = LoginPage(driver)
    login_page.navigate()
    
    for _ in range(5):
        login_page.login(credentials_lockout["email"], credentials_lockout["password_incorrect"])
        assert login_page.get_error_message() == "E-mail ou senha inválidos."
    
    login_page.login(credentials_lockout["email"], credentials_lockout["password_correct"])
    
    assert "bloqueada" in login_page.get_lockout_message().lower()
    assert login_page.is_on_page()

def test_tc_01_05_reset_contador_lockout(driver, credentials_lockout):
    login_page = LoginPage(driver)
    requests_page = RequestsPage(driver)
    login_page.navigate()
    
    for _ in range(4):
        login_page.login(credentials_lockout["email"], credentials_lockout["password_incorrect"])
        assert login_page.get_error_message() == "E-mail ou senha inválidos."
        
    login_page.login(credentials_lockout["email"], credentials_lockout["password_correct"])
    assert requests_page.is_table_visible()
    
    requests_page.logout()
    assert login_page.is_on_page()
    
    login_page.login(credentials_lockout["email"], credentials_lockout["password_incorrect"])
    assert login_page.get_error_message() == "E-mail ou senha inválidos."

def test_tc_01_06_email_invalido_formato(driver, credentials_invalid_email):
    login_page = LoginPage(driver)
    login_page.navigate()
    login_page.login(credentials_invalid_email["email"], credentials_invalid_email["password"])
    
    assert login_page.is_on_page()
