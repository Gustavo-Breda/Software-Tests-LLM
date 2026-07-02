from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


class RegisterPage:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.base_url = 'http://localhost:5173/register'

    def visit(self):
        self.driver.get(self.base_url)

    def fill_name(self, name):
        name_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@data-testid="register-name"]'))
        )
        name_input.send_keys(name)

    def fill_email(self, email):
        email_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@data-testid="register-email"]'))
        )
        email_input.send_keys(email)

    def fill_password(self, password):
        password_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@data-testid="register-password"]'))
        )
        password_input.send_keys(password)

    def click_submit(self):
        submit_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="register-submit"]'))
        )
        submit_button.click()

    def get_success_message(self):
        success_message = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="register-success"]'))
        )
        return success_message.text

    def get_error_message(self):
        error_message = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="register-error"]'))
        )
        return error_message.text


class LoginPage:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.base_url = 'http://localhost:5173/login'

    def visit(self):
        self.driver.get(self.base_url)

    def fill_email(self, email):
        email_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@data-testid="login-email"]'))
        )
        email_input.send_keys(email)

    def fill_password(self, password):
        password_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@data-testid="login-password"]'))
        )
        password_input.send_keys(password)

    def click_submit(self):
        submit_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="login-submit"]'))
        )
        submit_button.click()

    def get_error_message(self):
        error_message = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="login-error"]'))
        )
        return error_message.text

    def get_lockout_message(self):
        lockout_message = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="login-lockout"]'))
        )
        return lockout_message.text
