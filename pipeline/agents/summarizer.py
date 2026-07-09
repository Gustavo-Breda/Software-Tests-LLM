import json

from typing import Any
from pathlib import Path
from dataclasses import asdict, dataclass, field

from ..context import ContextBlob
from ..llm.adapter import LLMClient, LLMResponse
from .utils import (
    AgentOutputError,
    extract_json_object,
    load_prompt,
    validate_schema,
    wrap_raw_response_error,
)

_SYSTEM_PROMPT = (
    "Você responde apenas com JSON válido e segue estritamente o contrato solicitado."
)
_MAX_PYTEST_OUTPUT_CHARS = 8_000


@dataclass
class FailureSummary:
    caso_id: str
    categoria: str  # "sistema" | "teste" | "seletor" | "dado" | "ambiente"
    descricao: str
    evidencia: str


@dataclass
class CriterioCoverage:
    criterio_id: str
    coberto: bool
    casos_associados: list[str] = field(default_factory=list)


@dataclass
class SummarizerOutput:
    resumo: dict[str, Any] = field(default_factory=dict)
    falhas: list[FailureSummary] = field(default_factory=list)
    cobertura_por_criterio: list[CriterioCoverage] = field(default_factory=list)
    alertas_de_qualidade: list[str] = field(default_factory=list)
    proximos_passos: list[str] = field(default_factory=list)
    raw_response: LLMResponse | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw_response", None)
        return data


def run(pytest_output: str, blob: ContextBlob, client: LLMClient) -> SummarizerOutput:
    print(f"[summarizer] start story={blob.story_id} output_chars={len(pytest_output)}")
    prompt = _build_prompt(pytest_output, blob)
    response = client.complete(prompt, system=_SYSTEM_PROMPT, temperature=0.2, max_tokens=4096)
    try:
        data = extract_json_object(response.text)
        validate_schema(data, "summarizer_out.json")
    except AgentOutputError as exc:
        raise wrap_raw_response_error(exc, response) from exc
    output = SummarizerOutput(
        resumo=data["resumo"],
        falhas=[FailureSummary(**f) for f in data["falhas"]],
        cobertura_por_criterio=[CriterioCoverage(**c) for c in data["cobertura_por_criterio"]],
        alertas_de_qualidade=data["alertas_de_qualidade"],
        proximos_passos=data["proximos_passos"],
        raw_response=response,
    )
    print(
        f"[summarizer] done story={blob.story_id} "
        f"total={output.resumo.get('total_casos', 0)} "
        f"passed={output.resumo.get('aprovados', 0)} "
        f"failed={output.resumo.get('reprovados', 0)} "
        f"latency={response.latency_seconds:.2f}s"
    )
    return output


def save_report(output: SummarizerOutput, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(
        json.dumps(output.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _truncate_pytest_output(text: str) -> str:
    """Preserve the tail of pytest output (failures appear last)."""
    if len(text) <= _MAX_PYTEST_OUTPUT_CHARS:
        return text
    return "[... output truncado — início omitido ...]\n" + text[-_MAX_PYTEST_OUTPUT_CHARS:]


def _build_prompt(pytest_output: str, blob: ContextBlob) -> str:
    prompt = load_prompt("06_summarize.txt")
    criteria_lines = "\n".join(
        f"- {c.get('id', '?')}: {c.get('description', str(c))}"
        for c in blob.story.acceptance_criteria
    )
    replacements = {
        "pytest_output": _truncate_pytest_output(pytest_output),
        "acceptance_criteria": criteria_lines or "(sem critérios de aceitação disponíveis)",
    }
    for key, value in replacements.items():
        placeholder = "{" + key + "}"
        if placeholder not in prompt:
            raise AgentOutputError(f"Missing prompt placeholder: {placeholder}")
        prompt = prompt.replace(placeholder, value)
    return prompt
