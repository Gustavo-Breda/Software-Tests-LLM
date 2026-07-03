import json

import pytest

from pipeline.agents import agent1_generate
from pipeline.agents.utils import AgentOutputError
from pipeline.context import ContextBuilder
from pipeline.llm.adapter import LLMClient, LLMResponse


class FakeClient(LLMClient):
    provider = "fake"

    def __init__(self, text: str | list[str]) -> None:
        super().__init__("fake-model")
        self.responses = [text] if isinstance(text, str) else text
        self.prompts: list[str] = []
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.prompts.append(prompt)
        self.calls.append(
            {
                "system": system,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        index = min(len(self.prompts) - 1, len(self.responses) - 1)
        return LLMResponse(text=self.responses[index], model=self.model, provider=self.provider)


def _blob():
    return ContextBuilder.from_repo().build("US-01")


def _blob_us03():
    return ContextBuilder.from_repo().build("US-03")


def _blob_us04():
    return ContextBuilder.from_repo().build("US-04")


def _valid_payload() -> dict:
    return {
        "test_cases": [
            {
                "id": "TC-01-01",
                "titulo": "Login bem-sucedido",
                "objetivo": "Validar login com credenciais corretas.",
                "criterios_cobertos": ["CA-01.1"],
                "tipo": "positivo",
                "prioridade": "alta",
                "pre_condicoes": ["Usuário alice@example.com existe."],
                "dados_de_teste": {
                    "email": "alice@example.com",
                    "password": "secret123"
                },
                "passos": [
                    "Acessar /login.",
                    "Preencher login-email com alice@example.com.",
                    "Preencher login-password com secret123.",
                    "Clicar em login-submit."
                ],
                "resultado_esperado": "Resposta 200 e redirecionamento para /requests.",
                "automatizavel": True,
                "observacoes": ""
            },
            {
                "id": "TC-01-02",
                "titulo": "Login rejeitado com senha incorreta",
                "objetivo": "Validar mensagem genérica para senha incorreta.",
                "criterios_cobertos": ["CA-01.2"],
                "tipo": "negativo",
                "prioridade": "alta",
                "pre_condicoes": ["Usuário alice@example.com existe."],
                "dados_de_teste": {
                    "email": "alice@example.com",
                    "password": "SenhaErrada9"
                },
                "passos": ["Tentar login com os dados de teste."],
                "resultado_esperado": "Resposta 401 com 'E-mail ou senha inválidos.'.",
                "automatizavel": True,
                "observacoes": ""
            },
            {
                "id": "TC-01-03",
                "titulo": "Bloqueio após cinco falhas",
                "objetivo": "Validar lockout por 60 segundos.",
                "criterios_cobertos": ["CA-01.3"],
                "tipo": "borda",
                "prioridade": "alta",
                "pre_condicoes": ["Usuário alice@example.com existe."],
                "dados_de_teste": {
                    "email": "alice@example.com",
                    "password": "SenhaErrada9"
                },
                "passos": ["Executar cinco tentativas inválidas.", "Tentar login novamente."],
                "resultado_esperado": "Resposta 423 com header Retry-After.",
                "automatizavel": True,
                "observacoes": ""
            },
            {
                "id": "TC-01-04",
                "titulo": "Login rejeitado com e-mail em formato inválido",
                "objetivo": "Validar rejeição de e-mail sem formato válido.",
                "criterios_cobertos": ["CA-01.4"],
                "tipo": "negativo",
                "prioridade": "media",
                "pre_condicoes": [],
                "dados_de_teste": {
                    "email": "email_sem_arroba",
                    "password": "secret123"
                },
                "passos": ["Tentar login com e-mail inválido."],
                "resultado_esperado": "Resposta 422 e login não efetuado.",
                "automatizavel": True,
                "observacoes": ""
            }
        ],
        "matriz_rastreabilidade": [
            {"criterio": "CA-01.1", "casos": ["TC-01-01"]},
            {"criterio": "CA-01.2", "casos": ["TC-01-02"]},
            {"criterio": "CA-01.3", "casos": ["TC-01-03"]},
            {"criterio": "CA-01.4", "casos": ["TC-01-04"]}
        ],
        "alertas": []
    }


def test_agent1_accepts_valid_json():
    client = FakeClient(json.dumps(_valid_payload()))

    output = agent1_generate.run(_blob(), client)

    assert len(output.test_cases) == 4
    assert output.test_cases[0].id == "TC-01-01"
    assert "{user_story}" not in client.prompts[0]
    assert "{acceptance_criteria}" not in client.prompts[0]
    assert "{system_context}" not in client.prompts[0]
    assert "{few_shot_examples}" not in client.prompts[0]
    assert "{story_id}" not in client.prompts[0]
    assert "{test_case_id_prefix}" not in client.prompts[0]
    assert "TC-01-" in client.prompts[0]
    assert client.calls[0]["max_tokens"] == 20048


def test_agent1_rejects_malformed_json():
    client = FakeClient("não é JSON")

    with pytest.raises(AgentOutputError, match="valid JSON object"):
        agent1_generate.run(_blob(), client)


def test_agent1_rejects_schema_invalid_json():
    payload = _valid_payload()
    payload["test_cases"][0].pop("resultado_esperado")
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="Schema validation failed"):
        agent1_generate.run(_blob(), client)


def test_agent1_rejects_unknown_covered_criterion():
    payload = _valid_payload()
    payload["test_cases"][0]["criterios_cobertos"] = ["CA-99.1"]
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="unknown criteria"):
        agent1_generate.run(_blob(), client)


def test_agent1_normalizes_inconsistent_traceability_matrix():
    payload = _valid_payload()
    payload["matriz_rastreabilidade"][0]["casos"] = ["TC-01-02"]
    client = FakeClient(json.dumps(payload))

    output = agent1_generate.run(_blob(), client)

    assert output.matriz_rastreabilidade[0]["casos"] == ["TC-01-01"]


def test_agent1_retries_invalid_output_once():
    invalid = _valid_payload()
    invalid["test_cases"][0].pop("resultado_esperado")
    client = FakeClient([json.dumps(invalid), json.dumps(_valid_payload())])

    output = agent1_generate.run(_blob(), client)

    assert len(output.test_cases) == 4
    assert len(client.prompts) == 2
    assert "[CORREÇÃO OBRIGATÓRIA]" in client.prompts[1]
    assert client.calls[1]["temperature"] == 0.1


def test_agent1_normalizes_recoverable_contract_fields():
    payload = _valid_payload()
    payload.pop("alertas")
    payload["test_cases"][0].pop("automatizavel")
    payload["matriz_rastreabilidade"][0]["casos"] = []
    client = FakeClient(json.dumps(payload))

    output = agent1_generate.run(_blob(), client)

    assert output.alertas == []
    assert output.test_cases[0].automatizavel is True
    assert output.matriz_rastreabilidade[0]["casos"] == ["TC-01-01"]


def test_agent1_normalizes_us_prefixed_case_ids():
    payload = _valid_payload()
    payload["test_cases"][0]["id"] = "TC-US-01-01"
    payload["matriz_rastreabilidade"][0]["casos"] = ["TC-US-01-01"]
    client = FakeClient(json.dumps(payload))

    output = agent1_generate.run(_blob(), client)

    assert output.test_cases[0].id == "TC-01-01"
    assert output.matriz_rastreabilidade[0]["casos"] == ["TC-01-01"]


def test_agent1_normalizes_missing_repair_correction():
    payload = _valid_payload()
    client = FakeClient(json.dumps(payload))

    output = agent1_generate.run(
        _blob(),
        client,
        repair_feedback=json.dumps({"decisao": "REPROVADO"}),
        current_generation=agent1_generate.run(_blob(), FakeClient(json.dumps(_valid_payload()))),
    )

    assert output.test_cases[0].correcao_aplicada == "nenhuma - caso preservado"


def test_agent1_rejects_missing_criterion_coverage():
    payload = _valid_payload()
    payload["test_cases"][3]["criterios_cobertos"] = ["CA-01.1"]
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="CA-01.4 must be covered"):
        agent1_generate.run(_blob(), client)


def test_agent1_rejects_undocumented_selector():
    payload = _valid_payload()
    payload["test_cases"][0]["passos"].append("Clicar em login-fake.")
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="undocumented data-testid selectors"):
        agent1_generate.run(_blob(), client)


def test_agent1_rejects_false_short_title_boundary():
    payload = {
        "test_cases": [
            {
                "id": "TC-03-01",
                "titulo": "Criar solicitação válida",
                "objetivo": "Validar criação com dados válidos.",
                "criterios_cobertos": ["CA-03.1"],
                "tipo": "positivo",
                "prioridade": "alta",
                "pre_condicoes": ["Usuário autenticado."],
                "dados_de_teste": {
                    "titulo": "Título válido",
                    "descricao": "Descrição válida com tamanho suficiente.",
                    "prioridade": "alta",
                },
                "passos": ["Preencher request-title.", "Clicar em request-submit."],
                "resultado_esperado": "Resposta 201.",
                "automatizavel": True,
                "observacoes": "",
            },
            {
                "id": "TC-03-02",
                "titulo": "Título muito curto",
                "objetivo": "Validar título menor que 5.",
                "criterios_cobertos": ["CA-03.2"],
                "tipo": "negativo",
                "prioridade": "alta",
                "pre_condicoes": ["Usuário autenticado."],
                "dados_de_teste": {
                    "titulo": "Título Muito Curto",
                    "descricao": "Descrição válida com tamanho suficiente.",
                    "prioridade": "alta",
                },
                "passos": ["Preencher request-title com título curto."],
                "resultado_esperado": "Resposta 422.",
                "automatizavel": True,
                "observacoes": "",
            },
            {
                "id": "TC-03-03",
                "titulo": "Criar sem autenticação",
                "objetivo": "Validar criação sem token.",
                "criterios_cobertos": ["CA-03.3"],
                "tipo": "borda",
                "prioridade": "alta",
                "pre_condicoes": [],
                "dados_de_teste": {
                    "titulo": "Título válido",
                    "descricao": "Descrição válida com tamanho suficiente.",
                    "prioridade": "alta",
                },
                "passos": ["Enviar requisição sem token."],
                "resultado_esperado": "Resposta 401.",
                "automatizavel": True,
                "observacoes": "",
            },
        ],
        "matriz_rastreabilidade": [],
        "alertas": [],
    }
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="must have length < 5"):
        agent1_generate.run(_blob_us03(), client)


def test_agent1_rejects_exact_total_without_context_evidence():
    payload = {
        "test_cases": [
            {
                "id": "TC-04-01",
                "titulo": "Listar solicitações próprias",
                "objetivo": "Validar listagem sem filtros.",
                "criterios_cobertos": ["CA-04.1", "CA-04.2", "CA-04.3"],
                "tipo": "positivo",
                "prioridade": "alta",
                "pre_condicoes": ["Usuário autenticado."],
                "dados_de_teste": {"status": "aberta", "priority": "alta"},
                "passos": ["Acessar /requests."],
                "resultado_esperado": "Resposta 200 com total=9.",
                "automatizavel": True,
                "observacoes": "",
            }
        ],
        "matriz_rastreabilidade": [],
        "alertas": [],
    }
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="exact total 9"):
        agent1_generate.run(_blob_us04(), client)
