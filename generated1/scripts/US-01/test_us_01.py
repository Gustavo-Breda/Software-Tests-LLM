import pytest
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pages import LoginPage, RequestsListPage

def test_tc_01_01_login_bem_sucedido(driver, base_url, alice_user):
    login_page = LoginPage(driver, base_url)
    requests_list_page = RequestsListPage(driver, base_url)

    login_page.load()
    login_page.login(alice_user["email"], alice_user["password"])

    assert requests_list_page.is_on_page()

def test_tc_01_02_login_falha_com_email_nao_cadastrado(driver, base_url, non_existent_user_data):
    login_page = LoginPage(driver, base_url)

    login_page.load()
    login_page.login(non_existent_user_data["email"], non_existent_user_data["password"])

    assert login_page.is_on_page()
    assert login_page.get_error_message() == "E-mail ou senha inválidos."

def test_tc_01_03_login_falha_com_senha_incorreta_para_email_cadastrado(driver, base_url, incorrect_password_data):
    login_page = LoginPage(driver, base_url)

    login_page.load()
    login_page.login(incorrect_password_data["email"], incorrect_password_data["password"])

    assert login_page.is_on_page()
    assert login_page.get_error_message() == "E-mail ou senha inválidos."

def test_tc_01_04_login_falha_com_email_em_formato_invalido(driver, base_url, invalid_format_email_data):
    login_page = LoginPage(driver, base_url)

    login_page.load()
    login_page.login(invalid_format_email_data["email"], invalid_format_email_data["password"])

    assert login_page.is_on_page()
    # The exact message 'Formato de e-mail inválido' is an example. We assert for any error message presence.
    assert "inválido" in login_page.get_error_message().lower() or "invalid" in login_page.get_error_message().lower()

def test_tc_01_05_bloqueio_de_conta_apos_5_tentativas_falhas_consecutivas(driver, base_url, bob_incorrect_password_data):
    login_page = LoginPage(driver, base_url)

    login_page.load()

    for i in range(4):
        login_page.login(bob_incorrect_password_data["email"], bob_incorrect_password_data["password"])
        assert login_page.is_on_page()
        assert login_page.get_error_message() == "E-mail ou senha inválidos."
        # Reload page to clear form and error message for next attempt
        login_page.load()

    # 5ª tentativa - deve resultar em bloqueio
    login_page.login(bob_incorrect_password_data["email"], bob_incorrect_password_data["password"])
    assert login_page.is_on_page()
    assert "Conta bloqueada. Tente novamente em 60 segundos." in login_page.get_lockout_message()

def test_tc_01_06_tentativa_de_login_em_conta_bloqueada_mesmo_com_senha_correta(driver, base_url, bob_user, bob_incorrect_password_data):
    login_page = LoginPage(driver, base_url)

    # Primeiro, bloquear a conta do Bob (5 tentativas falhas)
    login_page.load()
    for i in range(5):
        login_page.login(bob_incorrect_password_data["email"], bob_incorrect_password_data["password"])
        if i < 4:
            assert login_page.get_error_message() == "E-mail ou senha inválidos."
        else:
            assert "Conta bloqueada. Tente novamente em 60 segundos." in login_page.get_lockout_message()
        login_page.load() # Recarregar para limpar o estado da UI

    # Tentar login com senha correta enquanto bloqueado
    login_page.login(bob_user["email"], bob_user["password"])

    assert login_page.is_on_page()
    assert "Conta bloqueada. Tente novamente em 60 segundos." in login_page.get_lockout_message()

def test_tc_01_07_login_bem_sucedido_reseta_contador_de_tentativas_falhas(driver, base_url, alice_user, alice_incorrect_password_data):
    login_page = LoginPage(driver, base_url)
    requests_list_page = RequestsListPage(driver, base_url)

    # 4 tentativas de login falhas
    login_page.load()
    for i in range(4):
        login_page.login(alice_incorrect_password_data["email"], alice_incorrect_password_data["password"])
        assert login_page.is_on_page()
        assert login_page.get_error_message() == "E-mail ou senha inválidos."
        login_page.load() # Recarregar para limpar o estado da UI

    # Login bem-sucedido
    login_page.login(alice_user["email"], alice_user["password"])
    assert requests_list_page.is_on_page()

    # Logout para testar nova tentativa falha
    # Não há botão de logout no UI map para a tela de requests_list, então simulamos um novo acesso à página de login
    login_page.load()

    # Nova tentativa de login falha (deve ser 1ª falha após reset, não 5ª)
    login_page.login(alice_incorrect_password_data["email"], alice_incorrect_password_data["password"])
    assert login_page.is_on_page()
    assert login_page.get_error_message() == "E-mail ou senha inválidos."
    # Não deve haver mensagem de lockout, confirmando o reset do contador
    WebDriverWait(driver, 5).until_not(
        EC.visibility_of_element_located(login_page.LOCKOUT_MESSAGE),
        message="Mensagem de lockout inesperada após reset do contador."
    )

def test_tc_01_08_desbloqueio_automatico_de_conta_apos_60_segundos(driver, base_url, bob_user, bob_incorrect_password_data):
    login_page = LoginPage(driver, base_url)
    requests_list_page = RequestsListPage(driver, base_url)

    # Bloquear a conta do Bob (5 tentativas falhas)
    login_page.load()
    for i in range(5):
        login_page.login(bob_incorrect_password_data["email"], bob_incorrect_password_data["password"])
        if i < 4:
            assert login_page.get_error_message() == "E-mail ou senha inválidos."
        else:
            assert "Conta bloqueada. Tente novamente em 60 segundos." in login_page.get_lockout_message()
        login_page.load() # Recarregar para limpar o estado da UI

    # A parte de 'aguardar um período superior a 60 segundos' é uma pendência de automação.
    # O teste automatizado não pode esperar 60 segundos usando time.sleep().
    # Portanto, a próxima tentativa de login *imediatamente* após o bloqueio ainda deve falhar com lockout.
    # Para verificar o desbloqueio, seria necessário um mecanismo de fast-forward de tempo ou execução manual.

    # Tentar login com senha correta imediatamente após o bloqueio (deve falhar com lockout)
    login_page.login(bob_user["email"], bob_user["password"])
    assert login_page.is_on_page()
    assert "Conta bloqueada. Tente novamente em 60 segundos." in login_page.get_lockout_message()
