import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()

@pytest.fixture
def credentials_valid():
    return {"email": "alice@example.com", "password": "Senha123"}

@pytest.fixture
def credentials_invalid_pass():
    return {"email": "alice@example.com", "password": "SenhaIncorreta99"}

@pytest.fixture
def credentials_nonexistent():
    return {"email": "inexistente@example.com", "password": "SenhaQualquer1"}

@pytest.fixture
def credentials_lockout():
    return {
        "email": "bob@example.com",
        "password_incorrect": "SenhaIncorreta9",
        "password_correct": "Senha123"
    }

@pytest.fixture
def credentials_invalid_email():
    return {"email": "bob_sem_arroba", "password": "Senha123"}
