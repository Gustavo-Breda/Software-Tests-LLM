from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time

class RequestsListPage:
    def __init__(self, driver):
        self.driver = driver
        self.filter_status = (By.XPATH, '//select[@data-testid="filter-status"]')
        self.filter_priority = (By.XPATH, '//select[@data-testid="filter-priority"]')
        self.requests_table = (By.XPATH, '//table[@data-testid="requests-table"]')
        self.row = (By.XPATH, '//tr[@data-testid="request-row"]')
        self.row_title = (By.XPATH, '//td[@data-testid="request-row-title"]')
        self.row_status = (By.XPATH, '//td[@data-testid="request-row-status"]')
        self.row_priority = (By.XPATH, '//td[@data-testid="request-row-priority"]')
        self.row_btn_cancel = (By.XPATH, '//button[@data-testid="request-row-cancel"]')
        self.empty_state = (By.XPATH, '//div[@data-testid="requests-empty"]')
        self.btn_logout = (By.XPATH, '//button[@data-testid="requests-logout"]')

    def select_status_filter(self, status):
        self.driver.find_element(*self.filter_status).send_keys(status)

    def select_priority_filter(self, priority):
        self.driver.find_element(*self.filter_priority).send_keys(priority)

    def get_requests_table(self):
        return self.driver.find_element(*self.requests_table)

    def get_request_rows(self):
        return self.driver.find_elements(*self.row)

    def get_request_row_title(self, row):
        return row.find_element(*self.row_title).text

    def get_request_row_status(self, row):
        return row.find_element(*self.row_status).text

    def get_request_row_priority(self, row):
        return row.find_element(*self.row_priority).text

    def click_cancel_button(self, row):
        row.find_element(*self.row_btn_cancel).click()

    def get_empty_state_text(self):
        return self.driver.find_element(*self.empty_state).text

    def click_logout_button(self):
        self.driver.find_element(*self.btn_logout).click()

class LoginPage:
    def __init__(self, driver):
        self.driver = driver
        self.input_email = (By.XPATH, '//input[@data-testid="login-email"]')
        self.input_password = (By.XPATH, '//input[@data-testid="login-password"]')
        self.btn_submit = (By.XPATH, '//button[@data-testid="login-submit"]')
        self.link_to_register = (By.XPATH, '//a[@data-testid="login-go-register"]')
        self.error_message = (By.XPATH, '//div[@data-testid="login-error"]')
        self.lockout_message = (By.XPATH, '//div[@data-testid="login-lockout"]')

    def login(self, email, password):
        self.driver.find_element(*self.input_email).send_keys(email)
        self.driver.find_element(*self.input_password).send_keys(password)
        self.driver.find_element(*self.btn_submit).click()

    def get_error_message(self):
        return self.driver.find_element(*self.error_message).text

    def get_lockout_message(self):
        return self.driver.find_element(*self.lockout_message).text

class RegisterPage:
    def __init__(self, driver):
        self.driver = driver
        self.input_name = (By.XPATH, '//input[@data-testid="register-name"]')
        self.input_email = (By.XPATH, '//input[@data-testid="register-email"]')
        self.input_password = (By.XPATH, '//input[@data-testid="register-password"]')
        self.btn_submit = (By.XPATH, '//button[@data-testid="register-submit"]')
        self.link_to_login = (By.XPATH, '//a[@data-testid="register-go-login"]')
        self.error_message = (By.XPATH, '//div[@data-testid="register-error"]')
        self.success_toast = (By.XPATH, '//div[@data-testid="register-success"]')

    def register(self, name, email, password):
        self.driver.find_element(*self.input_name).send_keys(name)
        self.driver.find_element(*self.input_email).send_keys(email)
        self.driver.find_element(*self.input_password).send,send_keys(password)
        self.driver.find_element(*self.btn_submit).click()

    def get_error_message(self):
        return self.driver.find_element(*self.error_message).text

    def get_success_toast(self):
        return self.driver.find_element(*self.success_toast).text

class RequestCreatePage:
    def __init__(self, driver):
        self.driver = driver
        self.input_title = (By.XPATH, '//input[@data-testid="request-title"]')
        self.input_description = (By.XPATH, '//input[@data-testid="request-description"]')
        self.select_priority = (By.XPATH, '//select[@data-testid="request-priority"]')
        self.btn_submit = (By.XPATH, '//button[@data-testid="request-submit"]')
        self.btn_cancel = (By.XPATH, '//button[@data-testid="request-cancel"]')
        self.error_message = (By.XPATH, '//div[@data-testid="request-error"]')

    def create_request(self, title, description, priority):
        self.driver.find_element(*self.input_title).send_keys(title)
        self.driver.find_element(*self.input_description).send_keys(description)
        self.driver.find_element(*self.select_priority).send_keys(priority)
        self.driver.find_element(*self.btn_submit).click()

    def get_error_message(self):
        return self.driver.find_element(*self.error_message).text

    def cancel_request(self):
        self.driver.find_element(*self.btn_cancel).click()

class CancelDialogPage:
    def __init__(self, driver):
        self.driver = driver
        self.dialog = (By.XPATH, '//div[@data-testid="cancel-dialog"]')
        self.dialog_title = (By.XPATH, '//h2[@data-testid="cancel-dialog-title"]')
        self.btn_confirm = (By.XPATH, '//button[@data-testid="cancel-confirm"]')
        self.btn_back = (By.XPATH, '//button[@data-testid="cancel-back"]')

    def get_dialog_title(self):
        return self.driver.find_element(*self.dialog_title).text

    def confirm_cancel(self):
        self.driver.find_element(*self.btn_confirm).click()

    def go_back(self):
        self.driver.find_element(*self.btn_back).click()
