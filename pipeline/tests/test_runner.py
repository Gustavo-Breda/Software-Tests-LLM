import json
from unittest.mock import MagicMock, patch

from pipeline.context import ContextBuilder
from pipeline.agents.utils import RawAgentResponseError
from pipeline.llm.adapter import LLMClient, LLMResponse
from pipeline.workflow.runner import _save_raw_error, run_phase4, run_phase5, run_phase6


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


def _agent1_repair_payload(story_number: str) -> dict:
    payload = _agent1_payload(story_number)
    for case in payload["test_cases"]:
        case["correcao_aplicada"] = "nenhuma - caso aprovado"
    return payload


def _agent2_approved_payload(story_number: str) -> dict:
    case_ids = [case["id"] for case in _agent1_payload(story_number)["test_cases"]]
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


def _agent3_payload(story_number: str) -> dict:
    cases = _agent1_payload(story_number)["test_cases"]
    test_functions = "\n\n".join(
        [
            (
                f"def test_{case['id'].lower().replace('-', '_')}_generated():\n"
                f"    # {case['id']}: {case['objetivo']}\n"
                "    assert True\n"
            )
            for case in cases
        ]
    )
    return {
        "arquivos": {
            "conftest.py": "import pytest\n",
            "pages.py": (
                "from selenium.webdriver.common.by import By\n\n"
                "class LoginPage:\n"
                "    EMAIL = (By.CSS_SELECTOR, '[data-testid=login-email]')\n"
            ),
            f"test_us_{story_number}.py": test_functions,
        },
        "pendencias_de_automacao": [],
    }


def _agent0_missing_recommendation_payload() -> dict:
    payload = _approved_payload("US-01")
    payload.pop("recomendacao")
    return payload


def _agent2_rejected_payload(story_number: str) -> dict:
    return {
        "status_geral": "REPROVADO",
        "pontuacao": {
            "cobertura": 7,
            "fidelidade_ao_requisito": 8,
            "clareza": 6,
            "automatizabilidade": 6,
        },
        "casos_aprovados": [f"TC-{story_number}-01"],
        "casos_reprovados": [f"TC-{story_number}-02"],
        "problemas": [
            {
                "caso_de_teste": f"TC-{story_number}-02",
                "tipo": "ambiguidade",
                "descricao": "Detalhamento insuficiente.",
                "evidencia_na_historia": f"CA-{story_number}.2",
                "acao_recomendada": "Detalhar passos e resultado esperado.",
            }
        ],
        "cenarios_omitidos_sugeridos": [],
        "decisao": "REPROVADO",
    }


def test_runner_keeps_agent0_blocks_and_runs_agent2_for_approved_stories(tmp_path):
    responses = [
        json.dumps(_approved_payload("US-01")),
        json.dumps(_agent1_payload("01")),
        json.dumps(_agent2_approved_payload("01")),
        json.dumps(_clarification_payload()),
        json.dumps(_approved_payload("US-03")),
        json.dumps(_agent1_payload("03")),
        json.dumps(_agent2_approved_payload("03")),
        json.dumps(_approved_payload("US-04")),
        json.dumps(_agent1_payload("04")),
        json.dumps(_agent2_approved_payload("04")),
        json.dumps(_approved_payload("US-05")),
        json.dumps(_agent1_payload("05")),
        json.dumps(_agent2_approved_payload("05")),
    ]
    client = SequenceClient(responses)

    aggregate, exit_code = run_phase4(
        client,
        agent0_reports_dir=tmp_path / "agent0",
        test_cases_dir=tmp_path / "test_cases",
        agent2_reports_dir=tmp_path / "agent2",
        repaired_test_cases_dir=tmp_path / "repaired",
    )

    assert exit_code == 1
    assert aggregate["total"] == 5
    assert aggregate["summary"]["agent0_ok"] == 5
    assert aggregate["summary"]["agent1_ok"] == 4
    assert aggregate["summary"]["agent2_ok"] == 4
    assert aggregate["summary"]["blocked"] == 1
    assert aggregate["summary"]["errors"] == 0
    assert aggregate["summary"]["repair_attempts"] == 0
    assert aggregate["blocked"][0]["story_id"] == "US-02"
    assert [item["story_id"] for item in aggregate["agent1"]] == ["US-01", "US-03", "US-04", "US-05"]
    assert [item["story_id"] for item in aggregate["agent2"]] == ["US-01", "US-03", "US-04", "US-05"]
    assert (tmp_path / "agent0" / "US-02.json").is_file()
    assert not (tmp_path / "test_cases" / "US-02.json").exists()
    assert (tmp_path / "test_cases" / "US-05.json").is_file()
    assert (tmp_path / "agent2" / "US-05_attempt-0.json").is_file()


def test_runner_saves_repair_attempts_and_fails_after_n(tmp_path):
    responses = [
        json.dumps(_approved_payload("US-01")),
        json.dumps(_agent1_payload("01")),
        json.dumps(_agent2_rejected_payload("01")),
        json.dumps(_agent1_repair_payload("01")),
        json.dumps(_agent2_rejected_payload("01")),
        json.dumps(_agent1_repair_payload("01")),
        json.dumps(_agent2_rejected_payload("01")),
        json.dumps(_agent1_repair_payload("01")),
        json.dumps(_agent2_rejected_payload("01")),
        json.dumps(_clarification_payload()),
        json.dumps(_approved_payload("US-03")),
        json.dumps(_agent1_payload("03")),
        json.dumps(_agent2_approved_payload("03")),
        json.dumps(_approved_payload("US-04")),
        json.dumps(_agent1_payload("04")),
        json.dumps(_agent2_approved_payload("04")),
        json.dumps(_approved_payload("US-05")),
        json.dumps(_agent1_payload("05")),
        json.dumps(_agent2_approved_payload("05")),
    ]
    client = SequenceClient(responses)

    aggregate, exit_code = run_phase4(
        client,
        agent0_reports_dir=tmp_path / "agent0",
        test_cases_dir=tmp_path / "test_cases",
        agent2_reports_dir=tmp_path / "agent2",
        repaired_test_cases_dir=tmp_path / "repaired",
    )

    assert exit_code == 1
    assert aggregate["summary"]["rejected_after_repair"] == 1
    assert aggregate["repair_attempts"][0] == {"story_id": "US-01", "count": 3}
    assert (tmp_path / "agent2" / "US-01_attempt-3.json").is_file()
    assert (tmp_path / "repaired" / "US-01_attempt-3.json").is_file()
    assert (tmp_path / "repaired" / "US-01_final.json").is_file()


def test_runner_phase5_generates_scripts_for_approved_stories(tmp_path):
    responses = []
    for story_number in ["01", "02", "03", "04", "05"]:
        responses.extend(
            [
                json.dumps(_approved_payload(f"US-{story_number}")),
                json.dumps(_agent1_payload(story_number)),
                json.dumps(_agent2_approved_payload(story_number)),
            ]
        )
    for story_number in ["01", "02", "03", "04", "05"]:
        responses.append(json.dumps(_agent3_payload(story_number)))
    client = SequenceClient(responses)

    aggregate, exit_code = run_phase5(
        client,
        agent0_reports_dir=tmp_path / "agent0",
        test_cases_dir=tmp_path / "test_cases",
        agent2_reports_dir=tmp_path / "agent2",
        repaired_test_cases_dir=tmp_path / "repaired",
        scripts_dir=tmp_path / "scripts",
    )

    assert exit_code == 0
    assert aggregate["summary"]["agent3_ok"] == 5
    assert aggregate["summary"]["agent3_skipped"] == 0
    assert (tmp_path / "scripts" / "US-01" / "test_us_01.py").is_file()
    assert (tmp_path / "scripts" / "US-05" / "pendencias_de_automacao.json").is_file()


def test_runner_saves_raw_response_for_validation_errors(tmp_path):
    responses = [
        json.dumps(_agent0_missing_recommendation_payload()),
        json.dumps(_approved_payload("US-02")),
        json.dumps(_agent1_payload("02")),
        json.dumps(_agent2_approved_payload("02")),
        json.dumps(_approved_payload("US-03")),
        json.dumps(_agent1_payload("03")),
        json.dumps(_agent2_approved_payload("03")),
        json.dumps(_approved_payload("US-04")),
        json.dumps(_agent1_payload("04")),
        json.dumps(_agent2_approved_payload("04")),
        json.dumps(_approved_payload("US-05")),
        json.dumps(_agent1_payload("05")),
        json.dumps(_agent2_approved_payload("05")),
    ]
    client = SequenceClient(responses)

    aggregate, exit_code = run_phase4(
        client,
        agent0_reports_dir=tmp_path / "agent0",
        test_cases_dir=tmp_path / "test_cases",
        agent2_reports_dir=tmp_path / "agent2",
        repaired_test_cases_dir=tmp_path / "repaired",
    )

    raw_path = tmp_path / "raw" / "agent0" / "US-01.json"
    assert exit_code == 1
    assert raw_path.is_file()
    assert aggregate["agent0"][0]["error"]["raw_response_path"] == str(raw_path)
    assert "raw_response" in json.loads(raw_path.read_text(encoding="utf-8"))


def test_runner_saves_raw_response_with_context_label_without_overwrite(tmp_path):
    first = RawAgentResponseError(
        "first error",
        raw_text='{"first": true}',
        provider="fake",
        model="fake-model",
        metadata={"context_label": "generate"},
    )
    second = RawAgentResponseError(
        "second error",
        raw_text='{"second": true}',
        provider="fake",
        model="fake-model",
        metadata={"context_label": "repair-attempt-1"},
    )

    first_path = _save_raw_error("agent1", "US-03", first, tmp_path)
    second_path = _save_raw_error("agent1", "US-03", second, tmp_path)

    assert first_path == tmp_path / "raw" / "agent1" / "US-03_generate.json"
    assert second_path == tmp_path / "raw" / "agent1" / "US-03_repair-attempt-1.json"
    assert json.loads(first_path.read_text(encoding="utf-8"))["context_label"] == "generate"
    assert json.loads(second_path.read_text(encoding="utf-8"))["raw_response"] == '{"second": true}'


def _summarizer_payload(story_number: str) -> dict:
    story = ContextBuilder.from_repo().build(f"US-{story_number}").story
    criteria = story.acceptance_criteria
    return {
        "resumo": {"total_casos": 1, "aprovados": 1, "reprovados": 0, "taxa_execucao": 1.0},
        "falhas": [],
        "cobertura_por_criterio": [
            {
                "criterio_id": c["id"],
                "coberto": True,
                "casos_associados": [f"TC-{story_number}-01"],
            }
            for c in criteria[:1]
        ],
        "alertas_de_qualidade": [],
        "proximos_passos": [],
    }


def test_runner_phase6_summarizes_test_results(tmp_path):
    script_dir = tmp_path / "scripts" / "US-01"
    script_dir.mkdir(parents=True)
    (script_dir / "test_us_01.py").write_text(
        "def test_tc_01_01_login_valido(): assert True\n"
    )

    fake_pytest_output = (
        "test_us_01.py::test_tc_01_01_login_valido PASSED\n"
        "1 passed in 0.1s"
    )
    client = SequenceClient([json.dumps(_summarizer_payload("01"))])

    mock_proc = MagicMock()
    mock_proc.stdout = fake_pytest_output
    mock_proc.stderr = ""
    mock_proc.returncode = 0

    with patch("pipeline.workflow.runner.subprocess.run", return_value=mock_proc):
        aggregate, exit_code = run_phase6(
            client,
            scripts_dir=tmp_path / "scripts",
            reports_dir=tmp_path / "reports",
        )

    assert exit_code == 0
    assert aggregate["summary"]["ok"] == 1
    assert aggregate["summary"]["errors"] == 0
    assert (tmp_path / "reports" / "US-01.json").is_file()
    report = json.loads((tmp_path / "reports" / "US-01.json").read_text())
    assert report["resumo"]["total_casos"] == 1
    assert report["resumo"]["aprovados"] == 1


def test_runner_phase6_fails_when_scripts_dir_missing(tmp_path):
    client = SequenceClient([])
    aggregate, exit_code = run_phase6(
        client,
        scripts_dir=tmp_path / "nonexistent",
        reports_dir=tmp_path / "reports",
    )
    assert exit_code == 1
    assert aggregate["summary"]["stories_processed"] == 0
