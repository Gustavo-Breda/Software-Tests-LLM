import json

import pytest

from pipeline.agents import agent0_quality_gate
from pipeline.agents.utils import AgentOutputError
from pipeline.context import ContextBuilder
from pipeline.llm.adapter import LLMClient, LLMResponse


class FakeClient(LLMClient):
    provider = "fake"

    def __init__(self, text: str) -> None:
        super().__init__("fake-model")
        self.text = text
        self.prompts: list[str] = []

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.prompts.append(prompt)
        return LLMResponse(text=self.text, model=self.model, provider=self.provider)


def _blob():
    return ContextBuilder.from_repo().build("US-01")


def _approved_payload() -> dict:
    return {
        "status": "APROVADA",
        "derivavel": True,
        "justificativa_derivabilidade": "Critérios claros e verificáveis.",
        "observacao_formato": "História segue o formato esperado.",
        "problemas": [],
        "recomendacao": "Prosseguir para geração de casos de teste.",
    }


def _clarification_payload() -> dict:
    return {
        "status": "PRECISA_DE_ESCLARECIMENTO",
        "derivavel": False,
        "justificativa_derivabilidade": "Falta dado necessário para derivar testes.",
        "observacao_formato": "Formato aceitável.",
        "problemas": [
            {
                "criterio_id": "CA-01.3",
                "tipo": "falta_de_dado",
                "descricao": "Não há regra para duração do bloqueio.",
                "impacto_em_testes": "Não é possível validar a janela de bloqueio.",
                "pergunta_para_o_product_owner": "Qual é a duração do bloqueio?",
            }
        ],
        "recomendacao": "Pedir esclarecimento ao Product Owner.",
    }


def test_agent0_accepts_valid_approved_json():
    client = FakeClient(json.dumps(_approved_payload()))

    output = agent0_quality_gate.run(_blob(), client)

    assert output.status == "APROVADA"
    assert output.derivavel is True
    assert output.problemas == []
    assert "{user_story}" not in client.prompts[0]
    assert "{acceptance_criteria}" not in client.prompts[0]
    assert "{system_context}" not in client.prompts[0]


def test_agent0_accepts_valid_clarification_json():
    client = FakeClient(json.dumps(_clarification_payload()))

    output = agent0_quality_gate.run(_blob(), client)

    assert output.status == "PRECISA_DE_ESCLARECIMENTO"
    assert output.derivavel is False
    assert output.problemas[0].tipo == "falta_de_dado"


def test_agent0_rejects_malformed_json():
    client = FakeClient("não é JSON")

    with pytest.raises(AgentOutputError, match="valid JSON object"):
        agent0_quality_gate.run(_blob(), client)


def test_agent0_rejects_schema_invalid_json():
    payload = _approved_payload()
    payload.pop("recomendacao")
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="Schema validation failed"):
        agent0_quality_gate.run(_blob(), client)


def test_agent0_rejects_inconsistent_strict_gate_json():
    payload = _approved_payload()
    payload["problemas"] = [
        {
            "criterio_id": "CA-01.1",
            "tipo": "ambiguidade",
            "descricao": "Termo vago.",
            "impacto_em_testes": "Teste pode assumir regra inexistente.",
            "pergunta_para_o_product_owner": "O que significa termo vago?",
        }
    ]
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="Strict gate violation"):
        agent0_quality_gate.run(_blob(), client)
