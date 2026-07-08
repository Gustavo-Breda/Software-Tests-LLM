from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class RegisterPage:
    _ROUTE = "/register"
    _LOGIN_ROUTE = "/login"

    _INPUT_NAME = (By.DATA_TEST_ID, "register-name")
    _INPUT_EMAIL = (By.DATA_TEST_ID, "register-email")
    _INPUT_PASSWORD = (By.DATA_TEST_ID, "register-password")
    _BTN_SUBMIT = (By.DATA_TEST_ID, "register-submit")
    _SUCCESS_TOAST = (By.DATA_TEST_ID, "register-success")
    _ERROR_MESSAGE = (By.DATA_TEST_ID, "register-error")

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 10)

    def go_to_register_page(self):
        self.driver.get(f"{self.base_url}{self._ROUTE}")
        self.wait.until(EC.url_to_be(f"{self.base_url}{self._ROUTE}"))

    def fill_registration_form(self, name, email, password):
        self.wait.until(EC.visibility_of_element_located(self._INPUT_NAME)).send_keys(name)
        self.driver.find_element(*self._INPUT_EMAIL).send_keys(email)
        self.driver.find_element(*self._INPUT_PASSWORD).send_keys(password)

    def submit_registration(self):
        self.wait.until(EC.element_to_be_clickable(self._BTN_SUBMIT)).click()

    def get_success_message(self):
        return self.wait.until(EC.visibility_of_element_located(self._SUCCESS_TOAST)).text

    def get_error_message(self):
        return self.wait.until(EC.visibility_of_element_located(self._ERROR_MESSAGE)).text

    def is_on_login_page(self):
        self.wait.until(EC.url_to_be(f"{self.base_url}{self._LOGIN_ROUTE}"))
        return self.driver.current_url == f"{self.base_url}{self._LOGIN_ROUTE}"

    def is_on_register_page(self):
        self.wait.until(EC.url_to_be(f"{self.base_url}{self._ROUTE}"))
        return self.driver.current_url == f"{self.base_url}{self._ROUTE}"
