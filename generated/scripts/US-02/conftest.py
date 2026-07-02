import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pages import RegisterPage, LoginPage


@pytest.fixture(scope='session')
def driver():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    yield driver
    driver.quit()


@pytest.fixture(scope='session')
def register_page(driver):
    return RegisterPage(driver)


@pytest.fixture(scope='session')
def login_page(driver):
    return LoginPage(driver)


@pytest.fixture(scope='session')
def base_url():
    return 'http://localhost:5173/register'


@pytest.fixture(scope='session')
def valid_user_data():
    return {
        'name': 'João Silva',
        'email': 'joao.silva@example.com',
        'password': 'Senha123'
    }


@pytest.fixture(scope='session')
def invalid_email_data():
    return {
        'name': 'Outra Alice',
        'email': 'alice@example.com',
        'password': 'OutraSenha9'
    }


@pytest.fixture(scope='session')
def invalid_password_no_number_data():
    return {
        'name': 'Diego Lima',
        'email': 'diego.lima@example.com',
        'password': 'apenasletras'
    }


@pytest.fixture(scope='session')
def invalid_name_short_data():
    return {
        'name': 'Eu',
        'email': 'eu@example.com',
        'password': 'Senha123'
    }


@pytest.fixture(scope='session')
def invalid_password_short_data():
    return {
        'name': 'Ana Souza',
        'email': 'ana.souza@example.com',
        'password': 'Senha12'
    }


@pytest.fixture(scope='session')
def invalid_name_long_data():
    return {
        'name': 'NomeMuitoLongoQueExcedeOlimiteDe80Caracteres',
        'email': 'nome@exemplo.com',
        'password': 'Senha123'
    }
