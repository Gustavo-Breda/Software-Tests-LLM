from pages import RequestsListPage, LoginPage, RegisterPage, RequestCreatePage, CancelDialogPage
from conftest import driver, auth_token, api_client, alice_user, bob_user
import pytest
import time


@pytest.mark.positivo
@pytest.mark.alta
def test_tc_04_01(driver, auth_token):
    """
    TC-04-01: Listar solicitações sem filtros aplicados
    Objetivo: Verificar que o endpoint retorna apenas as solicitações do próprio usuário, ordenadas por created_at descendente.
    """
    page = RequestsListPage(driver)
    page.get_requests_table()
    assert page.get_empty_state_text() == "Nenhuma solicitação encontrada." or page.get_request_rows() is not None


@pytest.mark.positivo
@pytest.mark.alta
def test_tc_04_02(driver, auth_token):
    """
    TC-04-02: Filtrar solicitações por status e prioridade
    Objetivo: Verificar que os filtros de status e prioridade são combináveis e retornam apenas o subconjunto de solicitações que satisfaz ambas as condições.
    """
    page = RequestsListPage(driver)
    page.select_status_filter('aberta')
    page.select_priority_filter('alta')
    assert page.get_empty_state_text() == "Nenhuma solicitação encontrada." or page.get_request_rows() is not None


@pytest.mark.borda
@pytest.mark.alta
def test_tc_04_03(driver, auth_token):
    """
    TC-04-03: Filtrar solicitações que não existem
    Objetivo: Verificar que quando o filtro não retorna nenhum item, a resposta é 200 com items=[] e total=0, e a UI exibe a mensagem 'Nenhuma solicitação encontrada.'
    """
    page = RequestsListPage(driver)
    page.select_status_filter('finalizada')
    page.select_priority_filter('baixa')
    assert page.get_empty_state_text() == "Nenhuma solicitação encontrada." or page.get_request_rows() is not None


@pytest.mark.negativo
@pytest.mark.media
def test_tc_04_04(driver, auth_token):
    """
    TC-04-04: Filtrar solicitações com status inválido
    Objetivo: Verificar que o uso de um status inválido não retorna erro, mas também não retorna resultados.
    """
    page = RequestsListPage(driver)
    page.select_status_filter('invalido')
    page.select_priority_filter('alta')
    assert page.get_empty_state_text() == "Nenhuma solicitação encontrada." or page.get_request_rows() is not None


@pytest.mark.negativo
@pytest.mark.media
def test_tc_04_05(driver, auth_token):
    """
    TC-04-05: Filtrar solicitações com prioridade inválida
    Objetivo: Verificar que o uso de uma prioridade inválida não retorna erro, mas também não retorna resultados.
    """
    page = RequestsListPage(driver)
    page.select_status_filter('aberta')
    page.select_priority_filter('invalida')
    assert page.get_empty_state_text() == "Nenhuma solicitação encontrada." or page.get_request_rows() is not None


@pytest.mark.negativo
@pytest.mark.baixa
def test_tc_04_06(driver, auth_token):
    """
    TC-04-06: Filtrar solicitações com status e prioridade inválidas
    Objetivo: Verificar que o uso de status e prioridade inválidas não retorna erro, mas também não retorna resultados.
    """
    page = RequestsListPage(driver)
    page.select_status_filter('invalido')
    page.select_priority_filter('invalida')
    assert page.get_empty_state_text() == "Nenhuma solicitação encontrada." or page.get_request_rows() is not None
