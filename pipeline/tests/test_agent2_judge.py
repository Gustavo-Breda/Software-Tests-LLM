import json

import pytest

from pipeline.agents import agent1_generate, agent2_judge
from pipeline.agents.utils import AgentOutputError
from pipeline.context import ContextBuilder
from pipeline.llm.adapter import LLMClient, LLMResponse


class SequenceClient(LLMClient):
    provider = "fake"

    def __init__(self, responses: list[str]) -> None:
        super().__init__("fake-model")
        self._responses = responses
        self._index = 0
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
        text = self._responses[self._index]
        self._index += 1
        return LLMResponse(text=text, model=self.model, provider=self.provider)


def _blob():
    return ContextBuilder.from_repo().build("US-01")


def _generation_payload(include_correction: bool = False) -> dict:
    payload = {
        "test_cases": [
            {
                "id": "TC-01-01",
                "titulo": "Login bem-sucedido",
                "objetivo": "Validar login com credenciais corretas.",
                "criterios_cobertos": ["CA-01.1"],
                "tipo": "positivo",
                "prioridade": "alta",
                "pre_condicoes": ["Usuário alice@example.com existe."],
                "dados_de_teste": {"email": "alice@example.com", "password": "secret123"},
                "passos": ["Acessar /login.", "Enviar credenciais válidas."],
                "resultado_esperado": "Resposta 200 e redirecionamento para /requests.",
                "automatizavel": True,
                "observacoes": "",
            },
            {
                "id": "TC-01-02",
                "titulo": "Login rejeitado com senha incorreta",
                "objetivo": "Validar mensagem genérica para senha incorreta.",
                "criterios_cobertos": ["CA-01.2"],
                "tipo": "negativo",
                "prioridade": "alta",
                "pre_condicoes": ["Usuário alice@example.com existe."],
                "dados_de_teste": {"email": "alice@example.com", "password": "SenhaErrada9"},
                "passos": ["Tentar login com senha incorreta."],
                "resultado_esperado": "Resposta 401 com mensagem genérica.",
                "automatizavel": True,
                "observacoes": "",
            },
            {
                "id": "TC-01-03",
                "titulo": "Bloqueio após cinco falhas",
                "objetivo": "Validar lockout por 60 segundos.",
                "criterios_cobertos": ["CA-01.3"],
                "tipo": "borda",
                "prioridade": "alta",
                "pre_condicoes": ["Usuário alice@example.com existe."],
                "dados_de_teste": {"email": "alice@example.com", "password": "SenhaErrada9"},
                "passos": ["Executar cinco tentativas inválidas.", "Tentar login novamente."],
                "resultado_esperado": "Resposta 423 com Retry-After.",
                "automatizavel": True,
                "observacoes": "",
            },
            {
                "id": "TC-01-04",
                "titulo": "Login rejeitado com e-mail em formato inválido",
                "objetivo": "Validar rejeição de e-mail sem formato válido.",
                "criterios_cobertos": ["CA-01.4"],
                "tipo": "negativo",
                "prioridade": "media",
                "pre_condicoes": [],
                "dados_de_teste": {"email": "email_sem_arroba", "password": "secret123"},
                "passos": ["Tentar login com e-mail inválido."],
                "resultado_esperado": "Resposta 422 e login não efetuado.",
                "automatizavel": True,
                "observacoes": "",
            },
        ],
        "matriz_rastreabilidade": [
            {"criterio": "CA-01.1", "casos": ["TC-01-01"]},
            {"criterio": "CA-01.2", "casos": ["TC-01-02"]},
            {"criterio": "CA-01.3", "casos": ["TC-01-03"]},
            {"criterio": "CA-01.4", "casos": ["TC-01-04"]},
        ],
        "alertas": [],
    }
    if include_correction:
        for case in payload["test_cases"]:
            case["correcao_aplicada"] = "nenhuma - caso aprovado"
    return payload


def _approved_judge_payload() -> dict:
    case_ids = [case["id"] for case in _generation_payload()["test_cases"]]
    return {
        "status_geral": "APROVADO",
        "pontuacao": {
            "cobertura": 10,
            "fidelidade_ao_requisito": 9,
            "clareza": 9,
            "automatizabilidade": 10,
        },
        "casos_aprovados": case_ids,
        "casos_reprovados": [],
        "problemas": [],
        "cenarios_omitidos_sugeridos": [],
        "decisao": "APROVADO",
    }


def _rejected_judge_payload() -> dict:
    return {
        "status_geral": "REPROVADO",
        "pontuacao": {
            "cobertura": 7,
            "fidelidade_ao_requisito": 8,
            "clareza": 6,
            "automatizabilidade": 6,
        },
        "casos_aprovados": ["TC-01-01", "TC-01-02", "TC-01-04"],
        "casos_reprovados": ["TC-01-03"],
        "problemas": [
            {
                "caso_de_teste": "TC-01-03",
                "tipo": "baixa_automatizabilidade",
                "descricao": "Passos vagos.",
                "evidencia_na_historia": "CA-01.3 exige bloqueio de 60 segundos.",
                "acao_recomendada": "Detalhar sequência de cinco falhas e nova tentativa.",
            }
        ],
        "cenarios_omitidos_sugeridos": [],
        "decisao": "REPROVADO",
    }


def _generation_output() -> agent1_generate.GenerationOutput:
    client = SequenceClient([json.dumps(_generation_payload())])
    return agent1_generate.run(_blob(), client)


def test_agent2_accepts_valid_approved_json():
    client = SequenceClient([json.dumps(_approved_judge_payload())])

    result = agent2_judge.run(_blob(), _generation_output(), client)

    assert result.final_output.decisao == "APROVADO"
    assert result.repair_attempts == 0
    assert len(result.attempt_reports) == 1
    assert "{generated_test_cases_json}" not in client.prompts[0]


def test_agent2_rejects_schema_invalid_json():
    payload = _approved_judge_payload()
    payload.pop("decisao")
    client = SequenceClient([json.dumps(payload)])

    with pytest.raises(AgentOutputError, match="Schema validation failed"):
        agent2_judge.run(_blob(), _generation_output(), client)


def test_agent2_rejects_score_out_of_range():
    payload = _approved_judge_payload()
    payload["pontuacao"]["cobertura"] = 11
    client = SequenceClient([json.dumps(payload)])

    with pytest.raises(AgentOutputError, match="Schema validation failed"):
        agent2_judge.run(_blob(), _generation_output(), client)


def test_agent2_rejects_unknown_case_ids():
    payload = _approved_judge_payload()
    payload["casos_aprovados"] = ["TC-99-99"]
    client = SequenceClient([json.dumps(payload)])

    with pytest.raises(AgentOutputError, match="unknown approved case IDs"):
        agent2_judge.run(_blob(), _generation_output(), client)


def test_agent2_rejects_approved_payload_with_problems():
    payload = _approved_judge_payload()
    payload["problemas"] = [
        {
            "caso_de_teste": "TC-01-01",
            "tipo": "ambiguidade",
            "descricao": "Há problema.",
            "evidencia_na_historia": "CA-01.1",
            "acao_recomendada": "Corrigir.",
        }
    ]
    client = SequenceClient([json.dumps(payload)])

    with pytest.raises(AgentOutputError, match="APROVADO must not contain"):
        agent2_judge.run(_blob(), _generation_output(), client)


def test_repair_uses_repair_prompt_and_requires_correcao_aplicada():
    client = SequenceClient([json.dumps(_generation_payload(include_correction=True))])

    output = agent1_generate.run(
        _blob(),
        client,
        repair_feedback=json.dumps(_rejected_judge_payload(), ensure_ascii=False),
        current_generation=_generation_output(),
    )

    assert len(output.test_cases) == 4
    assert "<judge_report>" in client.prompts[0]
    assert "{judge_report_json}" not in client.prompts[0]


def test_loop_stops_when_judge_approves_after_repair():
    client = SequenceClient(
        [
            json.dumps(_rejected_judge_payload()),
            json.dumps(_generation_payload(include_correction=True)),
            json.dumps(_approved_judge_payload()),
        ]
    )

    result = agent2_judge.run(_blob(), _generation_output(), client)

    assert result.final_output.decisao == "APROVADO"
    assert result.repair_attempts == 1
    assert len(result.repair_generations) == 1
    assert result.repair_generations[0].attempt == 1


def test_loop_fails_after_max_repairs():
    client = SequenceClient(
        [
            json.dumps(_rejected_judge_payload()),
            json.dumps(_generation_payload(include_correction=True)),
            json.dumps(_rejected_judge_payload()),
            json.dumps(_generation_payload(include_correction=True)),
            json.dumps(_rejected_judge_payload()),
            json.dumps(_generation_payload(include_correction=True)),
            json.dumps(_rejected_judge_payload()),
        ]
    )

    result = agent2_judge.run(_blob(), _generation_output(), client)

    assert result.final_output.decisao == "REPROVADO"
    assert result.repair_attempts == 3
    assert result.rejected_after_repair is True
    assert len(result.attempt_reports) == 4
