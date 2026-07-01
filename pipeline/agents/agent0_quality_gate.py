# Phase 3 — Agent 0: Story Quality Gate
#
# Avalia a user story e os critérios de aceitação ANTES de qualquer geração.
# Retorna APROVADA ou PRECISA_DE_ESCLARECIMENTO com problemas detalhados.
# Rubrica: critérios INVEST (Hernández-Agüero et al.) — Independent, Negotiable,
# Valuable, Estimable, Small, Testable.
#
# Prompt : pipeline/prompts/01_quality_gate.txt
# Schema : pipeline/schemas/agent0_out.json
import json
from dataclasses import asdict, dataclass, field
from typing import Any

import yaml

from ..llm.adapter import LLMClient, LLMResponse
from ..context import ContextBlob
from .utils import AgentOutputError, extract_json_object, load_prompt, validate_schema


_SYSTEM_PROMPT = (
    "Você responde apenas com JSON válido e segue estritamente o contrato solicitado."
)


@dataclass
class QualityGateProblem:
    criterio_id: str
    tipo: str
    descricao: str
    impacto_em_testes: str
    pergunta_para_o_product_owner: str


@dataclass
class QualityGateOutput:
    status: str
    derivavel: bool
    justificativa_derivabilidade: str
    observacao_formato: str
    problemas: list[QualityGateProblem] = field(default_factory=list)
    recomendacao: str = ""
    raw_response: LLMResponse | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw_response", None)
        return data


def run(blob: ContextBlob, client: LLMClient) -> QualityGateOutput:
    prompt = _build_prompt(blob)
    response = client.complete(
        prompt,
        system=_SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=2048,
    )
    data = extract_json_object(response.text)
    validate_schema(data, "agent0_out.json")
    _validate_strict_gate(data)
    return _to_output(data, response)


def _build_prompt(blob: ContextBlob) -> str:
    prompt = load_prompt("01_quality_gate.txt")
    story = blob.story
    story_payload = {
        "id": story.id,
        "title": story.title,
        "persona": story.persona,
        "acao": story.acao,
        "beneficio": story.beneficio,
        "touched_screens": story.touched_screens,
        "touched_endpoints": story.touched_endpoints,
    }
    replacements = {
        "user_story": yaml.safe_dump(story_payload, allow_unicode=True, sort_keys=False),
        "acceptance_criteria": yaml.safe_dump(
            story.acceptance_criteria,
            allow_unicode=True,
            sort_keys=False,
        ),
        "system_context": blob.text,
    }
    for key, value in replacements.items():
        placeholder = "{" + key + "}"
        if placeholder not in prompt:
            raise AgentOutputError(f"Missing prompt placeholder: {placeholder}")
        prompt = prompt.replace(placeholder, value)
    return prompt


def _validate_strict_gate(data: dict[str, Any]) -> None:
    status = data["status"]
    derivavel = data["derivavel"]
    problemas = data["problemas"]

    if status == "APROVADA" and (not derivavel or problemas):
        raise AgentOutputError(
            "Strict gate violation: APROVADA requires derivavel=true and problemas=[]."
        )
    if status == "PRECISA_DE_ESCLARECIMENTO" and derivavel and not problemas:
        raise AgentOutputError(
            "Strict gate violation: PRECISA_DE_ESCLARECIMENTO requires at least one problem or derivavel=false."
        )


def _to_output(data: dict[str, Any], response: LLMResponse) -> QualityGateOutput:
    return QualityGateOutput(
        status=data["status"],
        derivavel=data["derivavel"],
        justificativa_derivabilidade=data["justificativa_derivabilidade"],
        observacao_formato=data["observacao_formato"],
        problemas=[QualityGateProblem(**problem) for problem in data["problemas"]],
        recomendacao=data["recomendacao"],
        raw_response=response,
    )


def output_to_json(output: QualityGateOutput) -> str:
    return json.dumps(output.to_dict(), ensure_ascii=False, indent=2)
