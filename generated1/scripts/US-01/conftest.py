import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture(scope="session")
def base_url():
    return "http://localhost:5173"

@pytest.fixture(scope="function")
def driver(base_url):
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.implicitly_wait(5) # Implicit wait for element presence
    driver.get(base_url + "/login") # Start at login page for US-01 tests
    yield driver
    driver.quit()

@pytest.fixture
def alice_user():
    return {"email": "alice@example.com", "password": "Senha123"}

@pytest.fixture
def bob_user():
    return {"email": "bob@example.com", "password": "Senha123"}

@pytest.fixture
def non_existent_user_data():
    return {"email": "naoexiste@example.com", "password": "SenhaInvalida123"}

@pytest.fixture
def incorrect_password_data():
    return {"email": "alice@example.com", "password": "SenhaIncorreta123"}

@pytest.fixture
def invalid_format_email_data():
    return {"email": "email_sem_arroba", "password": "Senha123"}

@pytest.fixture
def bob_incorrect_password_data():
    return {"email": "bob@example.com", "password": "SenhaIncorreta"}

@pytest.fixture
def alice_incorrect_password_data():
    return {"email": "alice@example.com", "password": "SenhaIncorreta"}
