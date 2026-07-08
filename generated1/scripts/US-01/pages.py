from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class LoginPage:
    URL = "/login"
    INPUT_EMAIL = (By.CSS_SELECTOR, "[data-testid=login-email]")
    INPUT_PASSWORD = (By.CSS_SELECTOR, "[data-testid=login-password]")
    BTN_SUBMIT = (By.CSS_SELECTOR, "[data-testid=login-submit]")
    ERROR_MESSAGE = (By.CSS_SELECTOR, "[data-testid=login-error]")
    LOCKOUT_MESSAGE = (By.CSS_SELECTOR, "[data-testid=login-lockout]")

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def load(self):
        self.driver.get(self.base_url + self.URL)
        self.wait_for_page_load()

    def wait_for_page_load(self):
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.BTN_SUBMIT)
        )

    def enter_email(self, email):
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.INPUT_EMAIL)
        ).send_keys(email)

    def enter_password(self, password):
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.INPUT_PASSWORD)
        ).send_keys(password)

    def click_submit(self):
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.BTN_SUBMIT)
        ).click()

    def login(self, email, password):
        self.enter_email(email)
        self.enter_password(password)
        self.click_submit()

    def get_error_message(self):
        return WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.ERROR_MESSAGE)
        ).text

    def get_lockout_message(self):
        return WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.LOCKOUT_MESSAGE)
        ).text

    def is_on_page(self):
        return self.driver.current_url == self.base_url + self.URL

class RequestsListPage:
    URL = "/requests"

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def is_on_page(self):
        WebDriverWait(self.driver, 10).until(
            EC.url_to_be(self.base_url + self.URL)
        )
        return self.driver.current_url == self.base_url + self.URL
