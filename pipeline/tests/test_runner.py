import json

from pipeline.context import ContextBuilder
from pipeline.llm.adapter import LLMClient, LLMResponse
from pipeline.workflow.runner import run_phase3


class SequenceClient(LLMClient):
    provider = "fake"

    def __init__(self, responses: list[str]) -> None:
        super().__init__("fake-model")
        self._responses = responses
        self._index = 0

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        text = self._responses[self._index]
        self._index += 1
        return LLMResponse(text=text, model=self.model, provider=self.provider)


def _approved_payload(story_id: str) -> dict:
    return {
        "status": "APROVADA",
        "derivavel": True,
        "justificativa_derivabilidade": f"{story_id} derivável.",
        "observacao_formato": "Formato aceitável.",
        "problemas": [],
        "recomendacao": "Prosseguir.",
    }


def _clarification_payload() -> dict:
    return {
        "status": "PRECISA_DE_ESCLARECIMENTO",
        "derivavel": False,
        "justificativa_derivabilidade": "Falta regra.",
        "observacao_formato": "Formato aceitável.",
        "problemas": [
            {
                "criterio_id": "CA-02.1",
                "tipo": "omissao",
                "descricao": "Falta resultado observável.",
                "impacto_em_testes": "Agent 1 teria que inventar.",
                "pergunta_para_o_product_owner": "Qual é o resultado esperado?"
            }
        ],
        "recomendacao": "Pedir esclarecimento."
    }


def _agent1_payload(story_number: str) -> dict:
    story = ContextBuilder.from_repo().build(f"US-{story_number}").story
    criteria_ids = [criterion["id"] for criterion in story.acceptance_criteria]
    test_cases = []
    matrix = []

    for index, criterion_id in enumerate(criteria_ids, start=1):
        case_id = f"TC-{story_number}-{index:02d}"
        case_type = "positivo" if index == 1 else "borda" if index == len(criteria_ids) else "negativo"
        test_cases.append(
            {
                "id": case_id,
                "titulo": f"Caso para {criterion_id}",
                "objetivo": f"Validar {criterion_id}.",
                "criterios_cobertos": [criterion_id],
                "tipo": case_type,
                "prioridade": "alta" if index <= 2 else "media",
                "pre_condicoes": [],
                "dados_de_teste": {"campo": f"valor_{index}"},
                "passos": [f"Executar cenário {index}."],
                "resultado_esperado": f"Resultado esperado de {criterion_id} ocorre.",
                "automatizavel": True,
                "observacoes": ""
            }
        )
        matrix.append({"criterio": criterion_id, "casos": [case_id]})

    return {
        "test_cases": test_cases,
        "matriz_rastreabilidade": matrix,
        "alertas": []
    }


def test_runner_calls_agent1_only_for_agent0_approved_and_blocks_clarification(tmp_path):
    responses = [
        json.dumps(_approved_payload("US-01")),
        json.dumps(_agent1_payload("01")),
        json.dumps(_clarification_payload()),
        json.dumps(_approved_payload("US-03")),
        json.dumps(_agent1_payload("03")),
        json.dumps(_approved_payload("US-04")),
        json.dumps(_agent1_payload("04")),
        json.dumps(_approved_payload("US-05")),
        json.dumps(_agent1_payload("05")),
    ]
    client = SequenceClient(responses)

    aggregate, exit_code = run_phase3(
        client,
        agent0_reports_dir=tmp_path / "agent0",
        test_cases_dir=tmp_path / "test_cases",
    )

    assert exit_code == 1
    assert aggregate["total"] == 5
    assert aggregate["summary"]["agent0_ok"] == 5
    assert aggregate["summary"]["agent1_ok"] == 4
    assert aggregate["summary"]["blocked"] == 1
    assert aggregate["summary"]["errors"] == 0
    assert aggregate["blocked"][0]["story_id"] == "US-02"
    assert [item["story_id"] for item in aggregate["agent1"]] == ["US-01", "US-03", "US-04", "US-05"]
    assert (tmp_path / "agent0" / "US-02.json").is_file()
    assert not (tmp_path / "test_cases" / "US-02.json").exists()
    assert (tmp_path / "test_cases" / "US-05.json").is_file()
