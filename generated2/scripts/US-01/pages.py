from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class LoginPage:
    def __init__(self, driver):
        self.driver = driver
        self.url = "http://localhost:5173/login"
        self.email_input = (By.CSS_SELECTOR, "[data-testid=login-email]")
        self.password_input = (By.CSS_SELECTOR, "[data-testid=login-password]")
        self.submit_button = (By.CSS_SELECTOR, "[data-testid=login-submit]")
        self.error_msg = (By.CSS_SELECTOR, "[data-testid=login-error]")
        self.lockout_msg = (By.CSS_SELECTOR, "[data-testid=login-lockout]")

    def navigate(self):
        self.driver.get(self.url)

    def login(self, email, password):
        WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(self.email_input))
        email_el = self.driver.find_element(*self.email_input)
        email_el.clear()
        email_el.send_keys(email)
        
        pass_el = self.driver.find_element(*self.password_input)
        pass_el.clear()
        pass_el.send_keys(password)
        
        self.driver.find_element(*self.submit_button).click()

    def get_error_message(self):
        return WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.error_msg)
        ).text

    def get_lockout_message(self):
        return WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.lockout_msg)
        ).text

    def is_on_page(self):
        return "/login" in self.driver.current_url

class RequestsPage:
    def __init__(self, driver):
        self.driver = driver
        self.table = (By.CSS_SELECTOR, "[data-testid=requests-table]")
        self.logout_btn = (By.CSS_SELECTOR, "[data-testid=requests-logout]")

    def is_table_visible(self):
        try:
            WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(self.table))
            return True
        except:
            return False

    def logout(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.logout_btn)).click()
