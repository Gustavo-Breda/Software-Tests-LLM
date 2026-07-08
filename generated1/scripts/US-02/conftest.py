import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from pages import RegisterPage

@pytest.fixture(scope="session")
def base_url():
    return "http://localhost:5173"

@pytest.fixture(scope="session")
def api_base_url():
    return "http://localhost:8001"

@pytest.fixture(scope="function")
def driver(request):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

@pytest.fixture
def register_page(driver, base_url):
    return RegisterPage(driver, base_url)

# --- Fixtures para dados de teste US-02 ---

@pytest.fixture
def test_data_tc_02_01():
    return {
        "name": "Novo Usuario Teste",
        "email": "novo.usuario@example.com",
        "password": "SenhaValida123"
    }

@pytest.fixture
def test_data_tc_02_02():
    return {
        "name": "Outra Alice",
        "email": "alice@example.com",
        "password": "SenhaNova123"
    }

@pytest.fixture
def test_data_tc_02_03():
    return {
        "name": "Usuario Sem Numero",
        "email": "senha.sem.numero@example.com",
        "password": "ApenasLetras"
    }

@pytest.fixture
def test_data_tc_02_04():
    return {
        "name": "Usuario Sem Letra",
        "email": "senha.sem.letra@example.com",
        "password": "123456789"
    }

@pytest.fixture
def test_data_tc_02_05():
    return {
        "name": "Usuario Senha Curta",
        "email": "senha.curta@example.com",
        "password": "Scurta1"
    }

@pytest.fixture
def test_data_tc_02_06():
    return {
        "name": "Eu",
        "email": "nome.curto@example.com",
        "password": "SenhaValida1"
    }

@pytest.fixture
def test_data_tc_02_07():
    return {
        "name": "NomeMuitoLongoParaTesteComExatamenteOitentaCaracteresParaValidacaoDoLimiteSuperior",
        "email": "nome.80caracteres@example.com",
        "password": "SenhaValida123"
    }

@pytest.fixture
def test_data_tc_02_08():
    return {
        "name": "NomeMuitoLongoParaTesteComExatamenteOitentaEUmCaracteresParaValidacaoDoLimiteSuperiorX",
        "email": "nome.81caracteres@example.com",
        "password": "SenhaValida123"
    }

@pytest.fixture
def test_data_tc_02_09():
    return {
        "name": "Usuario Email Invalido",
        "email": "emailinvalido",
        "password": "SenhaValida123"
    }
