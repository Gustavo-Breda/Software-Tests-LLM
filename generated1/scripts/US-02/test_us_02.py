import pytest
import requests
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Nota: A verificação de status HTTP do backend é feita indiretamente via mensagens na UI
# ou, em casos específicos como TC-02-02, com chamadas diretas à API para verificar o estado.

def test_tc_02_01_cadastro_bem_sucedido(register_page, test_data_tc_02_01):
    register_page.go_to_register_page()
    register_page.fill_registration_form(
        test_data_tc_02_01["name"],
        test_data_tc_02_01["email"],
        test_data_tc_02_01["password"]
    )
    register_page.submit_registration()

    assert "Usuário cadastrado com sucesso!" in register_page.get_success_message()
    assert register_page.is_on_login_page()

def test_tc_02_02_rejeicao_email_existente(register_page, test_data_tc_02_02, api_base_url):
    register_page.go_to_register_page()
    register_page.fill_registration_form(
        test_data_tc_02_02["name"],
        test_data_tc_02_02["email"],
        test_data_tc_02_02["password"]
    )
    register_page.submit_registration()

    assert "E-mail já cadastrado." in register_page.get_error_message()
    assert register_page.is_on_register_page()

    # Verificar que a senha do usuário existente (alice@example.com) não foi alterada
    login_payload = {"email": "alice@example.com", "password": "Senha123"}
    response = requests.post(f"{api_base_url}/api/auth/login", json=login_payload)
    assert response.status_code == 200, "A senha de Alice foi alterada ou login falhou inesperadamente."

def test_tc_02_03_rejeicao_senha_sem_numero(register_page, test_data_tc_02_03):
    register_page.go_to_register_page()
    register_page.fill_registration_form(
        test_data_tc_02_03["name"],
        test_data_tc_02_03["email"],
        test_data_tc_02_03["password"]
    )
    register_page.submit_registration()

    assert register_page.get_error_message() is not None # Verifica que alguma mensagem de erro é exibida
    assert register_page.is_on_register_page()

def test_tc_02_04_rejeicao_senha_sem_letra(register_page, test_data_tc_02_04):
    register_page.go_to_register_page()
    register_page.fill_registration_form(
        test_data_tc_02_04["name"],
        test_data_tc_02_04["email"],
        test_data_tc_02_04["password"]
    )
    register_page.submit_registration()

    assert register_page.get_error_message() is not None
    assert register_page.is_on_register_page()

def test_tc_02_05_rejeicao_senha_curta(register_page, test_data_tc_02_05):
    register_page.go_to_register_page()
    register_page.fill_registration_form(
        test_data_tc_02_05["name"],
        test_data_tc_02_05["email"],
        test_data_tc_02_05["password"]
    )
    register_page.submit_registration()

    assert register_page.get_error_message() is not None
    assert register_page.is_on_register_page()

def test_tc_02_06_rejeicao_nome_curto(register_page, test_data_tc_02_06):
    register_page.go_to_register_page()
    register_page.fill_registration_form(
        test_data_tc_02_06["name"],
        test_data_tc_02_06["email"],
        test_data_tc_02_06["password"]
    )
    register_page.submit_registration()

    assert register_page.get_error_message() is not None
    assert register_page.is_on_register_page()

def test_tc_02_07_cadastro_nome_limite_superior(register_page, test_data_tc_02_07):
    register_page.go_to_register_page()
    register_page.fill_registration_form(
        test_data_tc_02_07["name"],
        test_data_tc_02_07["email"],
        test_data_tc_02_07["password"]
    )
    register_page.submit_registration()

    assert "Usuário cadastrado com sucesso!" in register_page.get_success_message()
    assert register_page.is_on_login_page()

def test_tc_02_08_rejeicao_nome_longo(register_page, test_data_tc_02_08):
    register_page.go_to_register_page()
    register_page.fill_registration_form(
        test_data_tc_02_08["name"],
        test_data_tc_02_08["email"],
        test_data_tc_02_08["password"]
    )
    register_page.submit_registration()

    assert register_page.get_error_message() is not None
    assert register_page.is_on_register_page()

def test_tc_02_09_rejeicao_email_invalido(register_page, test_data_tc_02_09):
    register_page.go_to_register_page()
    register_page.fill_registration_form(
        test_data_tc_02_09["name"],
        test_data_tc_02_09["email"],
        test_data_tc_02_09["password"]
    )
    register_page.submit_registration()

    assert register_page.get_error_message() is not None
    assert register_page.is_on_register_page()
