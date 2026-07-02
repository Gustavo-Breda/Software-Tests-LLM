import pytest
from pages import RegisterPage, LoginPage
from fixtures import valid_user_data, invalid_email_data, invalid_password_no_number_data, invalid_name_short_data, invalid_password_short_data, invalid_name_long_data


@pytest.mark.positive
@pytest.mark.high
def test_tc_02_01_register_success(valid_user_data):
    """
    TC-02-01: Cadastro bem-sucedido com dados válidos
    """
    register_page = RegisterPage(driver)
    register_page.visit()
    register_page.fill_name(valid_user_data['name'])
    register_page.fill_email(valid_user_data['email'])
    register_page.fill_password(valid_user_data['password'])
    register_page.click_submit()
    assert register_page.get_success_message() == 'Cadastro bem-sucedido! Redirecionando para o login.'
    assert driver.current_url == 'http://localhost:5173/login'


@pytest.mark.negative
@pytest.mark.high
def test_tc_02_02_register_duplicate_email(invalid_email_data):
    """
    TC-02-02: Rejeição ao cadastrar e-mail já existente
    """
    register_page = RegisterPage(driver)
    register_page.visit()
    register_page.fill_name(invalid_email_data['name'])
    register_page.fill_email(invalid_email_data['email'])
    register_page.fill_password(invalid_email_data['password'])
    register_page.click_submit()
    assert register_page.get_error_message() == 'E-mail já cadastrado.'


@pytest.mark.border
@pytest.mark.medium
def test_tc_02_03_register_password_no_number(invalid_password_no_number_data):
    """
    TC-02-03: Rejeição de senha sem número (só letras)
    """
    register_page = RegisterPage(driver)
    register_page.visit()
    register_page.fill_name(invalid_password_no_number_data['name'])
    register_page.fill_email(invalid_password_no_number_data['email'])
    register_page.fill_password(invalid_password_no_number_data['password'])
    register_page.click_submit()
    assert register_page.get_error_message() == 'Senha deve conter pelo menos um dígito e uma letra.'


@pytest.mark.border
@pytest.mark.low
def test_tc_02_04_register_name_short(invalid_name_short_data):
    """
    TC-02-04: Rejeição de nome com menos de 3 caracteres
    """
    register_page = RegisterPage(driver)
    register_page.visit()
    register_page.fill_name(invalid_name_short_data['name'])
    register_page.fill_email(invalid_name_short_data['email'])
    register_page.fill_password(invalid_name_short_data['password'])
    register_page.click_submit()
    assert register_page.get_error_message() == 'Nome deve ter entre 3 e 80 caracteres.'


@pytest.mark.border
@pytest.mark.medium
def test_tc_02_05_register_password_short(invalid_password_short_data):
    """
    TC-02-05: Rejeição de senha com menos de 8 caracteres
    """
    register_page = RegisterPage(driver)
    register_page.visit()
    register_page.fill_name(invalid_password_short_data['name'])
    register_page.fill_email(invalid_password_short_data['email'])
    register_page.fill_password(invalid_password_short_data['password'])
    register_page.click_submit()
    assert register_page.get_error_message() == 'Senha deve ter pelo menos 8 caracteres.'


@pytest.mark.border
@pytest.mark.low
def test_tc_02_06_register_name_long(invalid_name_long_data):
    """
    TC-02-06: Rejeição de nome com mais de 80 caracteres
    """
    register_page = RegisterPage(driver)
    register_page.visit()
    register_page.fill_name(invalid_name_long_data['name'])
    register_page.fill_email(invalid_name_long_data['email'])
    register_page.fill_password(invalid_name_long_data['password'])
    register_page.click_submit()
    assert register_page.get_error_message() == 'Nome deve ter entre 3 e 80 caracteres.'
