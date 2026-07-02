import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time


@pytest.fixture(scope='session')
def driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    yield driver
    driver.quit()

@pytest.fixture(scope='session')
def auth_token(driver):
    driver.get('http://localhost:5173/login')
    driver.find_element(By.XPATH, '//input[@data-testid="login-email"]').send_keys('alice@example.com')
    driver.find_element(By.XPATH, '//input[@data-testid="login-password"]').send_keys('Senha123')
    driver.find_element(By.XPATH, '//button[@data-testid="login-submit"]').click()
    
    # Wait for token to be available
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//button[@data-testid="requests-logout"]'))
    )
    
    # Extract token from response
    token = driver.get_cookie('Authorization')['value'].split(' ')[1]
    return token

@pytest.fixture(scope='session')
def api_client(driver, auth_token):
    def get(url, params=None):
        driver.get(f'http://localhost:8001{url}')
        if params:
            driver.get(f'http://localhost:8001{url}?{params}')
        return driver.page_source
    
    def post(url, data=None):
        driver.get(f'http://localhost:8001{url}')
        if data:
            driver.find_element(By.XPATH, '//input[@data-testid="request-title"]').send_keys(data['title'])
            driver.find_element(By.XPATH, '//input[@data-testid="request-description"]').send_keys(data['description'])
            driver.find_element(By.XPATH, '//select[@data-testid="request-priority"]').send_keys(data['priority'])
            driver.find_element(By.XPATH, '//button[@data-testid="request-submit"]').click()
        return driver.page_source
    
    return {
        'get': get,
        'post': post
    }

@pytest.fixture(scope='session')
def alice_user(driver, auth_token):
    driver.get('http://localhost:5173/requests')
    return 'alice@example.com'

@pytest.fixture(scope='session')
def bob_user(driver, auth_token):
    driver.get('http://localhost:5173/requests')
    return 'bob@example.com'
