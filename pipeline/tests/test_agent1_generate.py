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
    assert client.calls[0]["max_tokens"] == 8192


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
