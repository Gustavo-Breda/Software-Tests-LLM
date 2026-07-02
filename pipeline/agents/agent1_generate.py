# Phase 3 — Agent 1: Test Case Generation
#
# Gera casos de teste estruturados (JSON) a partir da story + contexto.
# Também é chamado na fase de reparo (Phase 4) com o prompt 04_repair.txt
# e o feedback do juiz — NÃO criar uma função separada para reparo,
# só trocar o prompt e adicionar o campo "correcao_aplicada" no output.
#
# Técnicas: Equivalence Partitioning + Boundary Analysis; persona de QA Sênior/ISTQB.
# Prompt geração : pipeline/prompts/02_generate.txt
# Prompt reparo  : pipeline/prompts/04_repair.txt
# Schema         : pipeline/schemas/agent1_out.json
#
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
class TestCase:
    id: str
    titulo: str
    objetivo: str
    criterios_cobertos: list[str]
    tipo: str
    prioridade: str
    pre_condicoes: list[str]
    dados_de_teste: dict[str, Any]
    passos: list[str]
    resultado_esperado: str
    automatizavel: bool
    observacoes: str = ""
    correcao_aplicada: str = ""     # preenchido apenas no ciclo de reparo


@dataclass
class GenerationOutput:
    test_cases: list[TestCase] = field(default_factory=list)
    matriz_rastreabilidade: list[dict[str, Any]] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    raw_response: LLMResponse | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw_response", None)
        return data


def run(
    blob: ContextBlob,
    client: LLMClient,
    *,
    repair_feedback: str | None = None,
) -> GenerationOutput:
    if repair_feedback is not None:
        raise NotImplementedError("Repair flow belongs to Phase 4.")

    prompt = _build_prompt(blob)
    response = client.complete(
        prompt,
        system=_SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=4096,
    )
    data = extract_json_object(response.text)
    validate_schema(data, "agent1_out.json")
    _validate_semantics(blob, data)
    return _to_output(data, response)


def _build_prompt(blob: ContextBlob) -> str:
    prompt = load_prompt("02_generate.txt")
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
        "system_context": blob.filtered_text({
            "Glossário de Domínio",
            "Exemplo aprovado (referência de formato)",
            "História do Usuário e Critérios de Aceitação",
        }),
        "domain_glossary": _section_body(blob, "Glossário de Domínio"),
        "few_shot_examples": _section_body(blob, "Exemplo aprovado (referência de formato)"),
    }
    for key, value in replacements.items():
        placeholder = "{" + key + "}"
        if placeholder not in prompt:
            raise AgentOutputError(f"Missing prompt placeholder: {placeholder}")
        prompt = prompt.replace(placeholder, value)
    return prompt


def _section_body(blob: ContextBlob, title: str) -> str:
    for section in blob.sections:
        if section.title == title:
            return section.body
    return ""


def _validate_semantics(blob: ContextBlob, data: dict[str, Any]) -> None:
    valid_criteria = {
        str(criterion.get("id"))
        for criterion in blob.story.acceptance_criteria
        if criterion.get("id")
    }
    story_number = blob.story_id.removeprefix("US-")
    expected_prefix = f"TC-{story_number}-"

    cases = data["test_cases"]
    case_ids = [case["id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise AgentOutputError("Agent 1 semantic validation failed: duplicate test case IDs.")

    case_by_id = {case["id"]: case for case in cases}
    for case in cases:
        if not case["id"].startswith(expected_prefix):
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: {case['id']} does not match {expected_prefix}NN."
            )
        covered = set(case["criterios_cobertos"])
        unknown = covered - valid_criteria
        if unknown:
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: {case['id']} references unknown criteria {sorted(unknown)}."
            )
        _validate_string_list(case["pre_condicoes"], f"{case['id']}.pre_condicoes")
        _validate_string_list(case["passos"], f"{case['id']}.passos")

    matrix = data["matriz_rastreabilidade"]
    matrix_criteria = [entry["criterio"] for entry in matrix]
    if len(matrix_criteria) != len(set(matrix_criteria)):
        raise AgentOutputError("Agent 1 semantic validation failed: duplicate matrix criteria.")
    if set(matrix_criteria) != valid_criteria:
        raise AgentOutputError(
            "Agent 1 semantic validation failed: matrix criteria must match acceptance criteria."
        )

    matrix_by_criterion = {entry["criterio"]: set(entry["casos"]) for entry in matrix}
    for criterion, matrix_cases in matrix_by_criterion.items():
        unknown_cases = matrix_cases - set(case_ids)
        if unknown_cases:
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: matrix for {criterion} references unknown cases {sorted(unknown_cases)}."
            )

    for case_id, case in case_by_id.items():
        for criterion in case["criterios_cobertos"]:
            if case_id not in matrix_by_criterion.get(criterion, set()):
                raise AgentOutputError(
                    f"Agent 1 semantic validation failed: {case_id} covers {criterion} but matrix does not list it."
                )

    for criterion, matrix_cases in matrix_by_criterion.items():
        for case_id in matrix_cases:
            if criterion not in case_by_id[case_id]["criterios_cobertos"]:
                raise AgentOutputError(
                    f"Agent 1 semantic validation failed: matrix lists {case_id} for {criterion}, but case does not cover it."
                )


def _validate_string_list(values: list[str], location: str) -> None:
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: {location}[{index}] must be a non-empty string."
            )


def _to_output(data: dict[str, Any], response: LLMResponse) -> GenerationOutput:
    return GenerationOutput(
        test_cases=[TestCase(**case) for case in data["test_cases"]],
        matriz_rastreabilidade=data["matriz_rastreabilidade"],
        alertas=data["alertas"],
        raw_response=response,
    )


def output_to_json(output: GenerationOutput) -> str:
    return json.dumps(output.to_dict(), ensure_ascii=False, indent=2)
