import json
from pathlib import Path
from unittest.mock import MagicMock

from pipeline.context import ContextBuilder
from pipeline.llm.adapter import LLMClient, LLMResponse
from pipeline.agents.summarizer import (
    SummarizerOutput,
    FailureSummary,
    CriterioCoverage,
    _truncate_pytest_output,
    run,
    save_report,
)


class SingleResponseClient(LLMClient):
    provider = "fake"

    def __init__(self, response: str) -> None:
        super().__init__("fake-model")
        self._response = response

    def complete(self, prompt, *, system=None, temperature=0.2, max_tokens=1024) -> LLMResponse:
        return LLMResponse(text=self._response, model=self.model, provider=self.provider)


def _summarizer_payload(story_number: str) -> dict:
    return {
        "resumo": {
            "total_casos": 2,
            "aprovados": 1,
            "reprovados": 1,
            "taxa_execucao": 0.5,
        },
        "falhas": [
            {
                "caso_id": f"TC-{story_number}-02",
                "categoria": "seletor",
                "descricao": "data-testid não encontrado",
                "evidencia": "NoSuchElementException: no such element",
            }
        ],
        "cobertura_por_criterio": [
            {
                "criterio_id": f"CA-{story_number}.1",
                "coberto": True,
                "casos_associados": [f"TC-{story_number}-01"],
            },
            {
                "criterio_id": f"CA-{story_number}.2",
                "coberto": False,
                "casos_associados": [f"TC-{story_number}-02"],
            },
        ],
        "alertas_de_qualidade": ["Seletor ausente no ui_map para botão X"],
        "proximos_passos": ["Adicionar data-testid ao botão X no frontend"],
    }


def _blob(story_id: str):
    return ContextBuilder.from_repo().build(story_id)


def test_truncate_short_output_unchanged():
    text = "x" * 100
    assert _truncate_pytest_output(text) == text


def test_truncate_long_output_preserves_tail():
    tail = "FAILED test_tc_01_01"
    text = "x" * 9000 + tail
    result = _truncate_pytest_output(text)
    assert result.endswith(tail)
    assert len(result) <= 8_000 + 60  # marker overhead


def test_run_returns_summarizer_output():
    blob = _blob("US-01")
    payload = _summarizer_payload("01")
    client = SingleResponseClient(json.dumps(payload))
    pytest_output = "test_us_01.py::test_tc_01_01 PASSED\ntest_us_01.py::test_tc_01_02 FAILED\n1 passed, 1 failed"

    output = run(pytest_output, blob, client)

    assert isinstance(output, SummarizerOutput)
    assert output.resumo["total_casos"] == 2
    assert output.resumo["aprovados"] == 1
    assert output.resumo["taxa_execucao"] == 0.5
    assert len(output.falhas) == 1
    assert isinstance(output.falhas[0], FailureSummary)
    assert output.falhas[0].categoria == "seletor"
    assert len(output.cobertura_por_criterio) == 2
    assert isinstance(output.cobertura_por_criterio[0], CriterioCoverage)
    assert output.cobertura_por_criterio[0].coberto is True
    assert output.cobertura_por_criterio[1].coberto is False


def test_run_raises_on_invalid_schema():
    from pipeline.agents.utils import RawAgentResponseError

    blob = _blob("US-01")
    bad_payload = {"resumo": {}, "falhas": [], "cobertura_por_criterio": []}
    client = SingleResponseClient(json.dumps(bad_payload))

    try:
        run("output", blob, client)
        assert False, "Expected RawAgentResponseError"
    except RawAgentResponseError:
        pass


def test_save_report_writes_json(tmp_path):
    output = SummarizerOutput(
        resumo={"total_casos": 1, "aprovados": 1, "reprovados": 0, "taxa_execucao": 1.0},
        falhas=[],
        cobertura_por_criterio=[
            CriterioCoverage(criterio_id="CA-01.1", coberto=True, casos_associados=["TC-01-01"])
        ],
        alertas_de_qualidade=[],
        proximos_passos=[],
    )
    dest = tmp_path / "reports" / "US-01.json"

    save_report(output, dest)

    assert dest.is_file()
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["resumo"]["total_casos"] == 1
    assert data["cobertura_por_criterio"][0]["criterio_id"] == "CA-01.1"
    assert "raw_response" not in data


def test_save_report_creates_parent_dirs(tmp_path):
    output = SummarizerOutput(
        resumo={"total_casos": 0, "aprovados": 0, "reprovados": 0, "taxa_execucao": 0.0},
        falhas=[],
        cobertura_por_criterio=[],
        alertas_de_qualidade=[],
        proximos_passos=[],
    )
    dest = tmp_path / "deep" / "nested" / "report.json"
    save_report(output, dest)
    assert dest.is_file()
