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
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import yaml

from ..llm.adapter import LLMClient, LLMResponse
from ..context import ContextBlob
from .utils import AgentOutputError, REPO_ROOT, extract_json_object, load_prompt, validate_schema, wrap_raw_response_error


_SYSTEM_PROMPT = (
    "Você responde apenas com JSON válido e segue estritamente o contrato solicitado."
)
_MAX_OUTPUT_REPAIR_ATTEMPTS = 2


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
    current_generation: "GenerationOutput | None" = None,
) -> GenerationOutput:
    is_repair = repair_feedback is not None
    mode = "repair" if is_repair else "generate"
    print(f"[agent1] start story={blob.story_id} mode={mode}")
    prompt = _build_prompt(
        blob,
        repair_feedback=repair_feedback,
        current_generation=current_generation,
    )
    last_error: AgentOutputError | None = None
    response: LLMResponse | None = None

    for attempt in range(_MAX_OUTPUT_REPAIR_ATTEMPTS + 1):
        response = client.complete(
            _repair_prompt(prompt, response.text, str(last_error)) if last_error and response else prompt,
            system=_SYSTEM_PROMPT,
            temperature=0.1 if attempt else 0.2,
            max_tokens=20_048,
        )
        try:
            data = extract_json_object(response.text)
            _normalize_contract_defaults(blob, data, repair_mode=is_repair)
            validate_schema(data, "agent1_out.json")
            _validate_semantics(blob, data, repair_mode=is_repair)
            break
        except AgentOutputError as exc:
            last_error = exc
            if attempt >= _MAX_OUTPUT_REPAIR_ATTEMPTS:
                raw_exc = wrap_raw_response_error(exc, response)
                raw_exc.metadata["context_label"] = mode
                raise raw_exc from exc
            print(
                f"[agent1] retry story={blob.story_id} mode={mode} "
                f"attempt={attempt + 1} reason={exc}"
            )
    else:
        raise AgentOutputError("Agent 1 failed to produce valid output.")

    assert response is not None
    output = _to_output(data, response)
    print(
        f"[agent1] done story={blob.story_id} mode={mode} "
        f"cases={len(output.test_cases)} alerts={len(output.alertas)} "
        f"latency={response.latency_seconds:.2f}s"
    )
    return output


def _repair_prompt(original_prompt: str, invalid_response: str, error: str) -> str:
    return (
        original_prompt
        + "\n\n[CORREÇÃO OBRIGATÓRIA]\n"
        + "Sua resposta anterior foi rejeitada pelo validador.\n"
        + f"Erro: {error}\n\n"
        + "Retorne novamente o JSON completo, corrigido, sem texto fora do JSON. "
        + "Não omita campos obrigatórios. Não reduza cobertura. Preserve casos "
        + "aprovados no feedback do Agent 2. Mantenha a matriz de rastreabilidade "
        + "consistente com criterios_cobertos."
    )


def _build_prompt(
    blob: ContextBlob,
    *,
    repair_feedback: str | None = None,
    current_generation: "GenerationOutput | None" = None,
) -> str:
    is_repair = repair_feedback is not None
    if is_repair and current_generation is None:
        raise AgentOutputError("Repair flow requires current_generation.")

    prompt = load_prompt("04_repair.txt" if is_repair else "02_generate.txt")
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
    story_number = story.id.removeprefix("US-")
    replacements = {
        "story_id": story.id,
        "test_case_id_prefix": f"TC-{story_number}-",
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
    }
    if is_repair:
        replacements["generated_test_cases_json"] = output_to_json(current_generation)
        replacements["judge_report_json"] = repair_feedback
    else:
        replacements["domain_glossary"] = _section_body(blob, "Glossário de Domínio")
        replacements["few_shot_examples"] = _section_body(
            blob,
            "Exemplo aprovado (referência de formato)",
        )
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


def _normalize_contract_defaults(
    blob: ContextBlob,
    data: dict[str, Any],
    *,
    repair_mode: bool = False,
) -> None:
    data.setdefault("alertas", [])
    story_number = blob.story_id.removeprefix("US-")
    valid_criteria = [
        str(criterion.get("id"))
        for criterion in blob.story.acceptance_criteria
        if criterion.get("id")
    ]
    cases = data.get("test_cases")
    if not isinstance(cases, list):
        return

    for case in cases:
        if not isinstance(case, dict):
            continue
        if "id" in case:
            case["id"] = _normalize_case_id(str(case["id"]), story_number)
        case.setdefault("automatizavel", True)
        case.setdefault("observacoes", "")
        if repair_mode:
            case.setdefault("correcao_aplicada", "nenhuma - caso preservado")

    matrix = []
    for criterion in valid_criteria:
        matrix.append(
            {
                "criterio": criterion,
                "casos": [
                    case["id"]
                    for case in cases
                    if isinstance(case, dict)
                    and criterion in case.get("criterios_cobertos", [])
                    and "id" in case
                ],
            }
        )
    data["matriz_rastreabilidade"] = matrix


def _normalize_case_id(case_id: str, story_number: str) -> str:
    match = re.fullmatch(r"TC-?US-?0?(\d{1,2})-(\d{1,2})", case_id, flags=re.IGNORECASE)
    if match and match.group(1).zfill(2) == story_number:
        return f"TC-{story_number}-{match.group(2).zfill(2)}"

    match = re.fullmatch(r"TC-0?(\d{1,2})-(\d{1,2})", case_id, flags=re.IGNORECASE)
    if match and match.group(1).zfill(2) == story_number:
        return f"TC-{story_number}-{match.group(2).zfill(2)}"

    return case_id


def _validate_semantics(
    blob: ContextBlob,
    data: dict[str, Any],
    *,
    repair_mode: bool = False,
) -> None:
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
        if repair_mode and not str(case.get("correcao_aplicada", "")).strip():
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: {case['id']} must include correcao_aplicada during repair."
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
        if not repair_mode and not matrix_cases:
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: {criterion} must be covered by at least one test case."
            )
        for case_id in matrix_cases:
            if criterion not in case_by_id[case_id]["criterios_cobertos"]:
                raise AgentOutputError(
                    f"Agent 1 semantic validation failed: matrix lists {case_id} for {criterion}, but case does not cover it."
                )

    _validate_documented_selectors(cases)
    _validate_no_unsupported_exact_totals(blob, cases)
    _validate_boundary_values(blob, cases)


def _validate_string_list(values: list[str], location: str) -> None:
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: {location}[{index}] must be a non-empty string."
            )


def _validate_documented_selectors(cases: list[dict[str, Any]]) -> None:
    documented = _documented_testids()
    referenced: set[str] = set()
    for case in cases:
        text = _case_text(case)
        referenced.update(re.findall(r"data-testid[=\s:'\"\[]+([a-z0-9_-]+)", text, flags=re.IGNORECASE))
        referenced.update(re.findall(r"\b(?:login|register|request|requests|filter|cancel)-[a-z0-9_-]+\b", text))

    unknown = sorted(selector for selector in referenced if selector not in documented)
    if unknown:
        raise AgentOutputError(
            f"Agent 1 semantic validation failed: undocumented data-testid selectors {unknown}."
        )


def _documented_testids() -> set[str]:
    path = REPO_ROOT / "pipeline" / "context" / "ui_map.json"
    ui_map = json.loads(path.read_text(encoding="utf-8"))
    selectors: set[str] = set()
    for screen in ui_map.get("screens", {}).values():
        for selector in screen.get("selectors", {}).values():
            match = re.search(r"data-testid=([^\]]+)", str(selector))
            if match:
                selectors.add(match.group(1))
    return selectors


def _validate_no_unsupported_exact_totals(blob: ContextBlob, cases: list[dict[str, Any]]) -> None:
    context_text = _normalise_text(blob.text)
    pattern = re.compile(
        r"\b(?:total|quantidade|listar|exibir|mostrar)\D{0,24}(\d+)\b",
        flags=re.IGNORECASE,
    )
    for case in cases:
        for number in pattern.findall(_case_text(case)):
            if not _has_exact_total_evidence(context_text, number):
                raise AgentOutputError(
                    f"Agent 1 semantic validation failed: {case['id']} asserts exact total {number} without context evidence."
                )


def _validate_boundary_values(blob: ContextBlob, cases: list[dict[str, Any]]) -> None:
    criteria_by_id = {
        str(criterion.get("id")): _criterion_text(criterion)
        for criterion in blob.story.acceptance_criteria
        if criterion.get("id")
    }
    for case in cases:
        criteria_text = " ".join(criteria_by_id[criterion] for criterion in case["criterios_cobertos"])
        criteria_norm = _normalise_text(criteria_text)
        data = case.get("dados_de_teste", {})
        if not isinstance(data, dict):
            continue

        _validate_length_boundary(case, data, criteria_norm)
        _validate_password_boundaries(case, data, criteria_norm)
        _validate_priority_enum(case, data, criteria_norm)


def _validate_length_boundary(case: dict[str, Any], data: dict[str, Any], criteria_text: str) -> None:
    for field_name, value in data.items():
        if not isinstance(value, str):
            continue
        field_norm = _normalise_text(str(field_name))
        if "titulo" in field_norm or "title" in field_norm:
            _assert_text_boundary(case, field_name, value, criteria_text, "titulo")
        if "descricao" in field_norm or "description" in field_norm:
            _assert_text_boundary(case, field_name, value, criteria_text, "descricao")
        if "nome" in field_norm or "name" in field_norm:
            _assert_text_boundary(case, field_name, value, criteria_text, "nome")


def _assert_text_boundary(
    case: dict[str, Any],
    field_name: str,
    value: str,
    criteria_text: str,
    requirement_name: str,
) -> None:
    case_text = _normalise_text(_case_text(case))
    if requirement_name not in case_text:
        return

    # Check shorter boundary (only if case targets shorter/minor/minimum limits)
    if any(marker in case_text for marker in ("menor", "curt", "min", "inf")):
        shorter_match = re.search(rf"{requirement_name}[^.。;,]*menor (?:que|do que) (\d+)", criteria_text)
        if shorter_match:
            limit = int(shorter_match.group(1))
            if len(value) >= limit:
                raise AgentOutputError(
                    f"Agent 1 semantic validation failed: {case['id']} field {field_name} must have length < {limit}."
                )

    # Check longer boundary (only if case targets longer/major/maximum limits)
    if any(marker in case_text for marker in ("maior", "long", "max", "sup")):
        longer_match = re.search(rf"{requirement_name}[^.。;,]*maior (?:que|do que) (\d+)", criteria_text)
        if longer_match:
            limit = int(longer_match.group(1))
            if len(value) <= limit:
                raise AgentOutputError(
                    f"Agent 1 semantic validation failed: {case['id']} field {field_name} must have length > {limit}."
                )


def _validate_password_boundaries(case: dict[str, Any], data: dict[str, Any], criteria_text: str) -> None:
    password_items = [
        (str(field_name), value)
        for field_name, value in data.items()
        if isinstance(value, str)
        and (
            "password" in _normalise_text(str(field_name))
            or "senha" in _normalise_text(str(field_name))
        )
    ]
    if not password_items:
        return

    case_text = _normalise_text(_case_text(case))
    for field_name, value in password_items:
        if "senha" in criteria_text and "menor que 8" in criteria_text and "curt" in case_text and len(value) >= 8:
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: {case['id']} field {field_name} must have length < 8."
            )
        if "sem letra" in case_text and any(char.isalpha() for char in value):
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: {case['id']} field {field_name} must not contain letters."
            )
        if "sem numero" in case_text and any(char.isdigit() for char in value):
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: {case['id']} field {field_name} must not contain numbers."
            )


def _validate_priority_enum(case: dict[str, Any], data: dict[str, Any], criteria_text: str) -> None:
    if "prioridade" not in criteria_text or "fora do enum" not in criteria_text:
        return
    case_text = _normalise_text(_case_text(case))
    if "fora do enum" not in case_text and "invalida" not in case_text:
        return
    valid = {"baixa", "media", "alta"}
    for field_name, value in data.items():
        if "prior" not in _normalise_text(str(field_name)) or not isinstance(value, str):
            continue
        if _normalise_text(value) in valid:
            raise AgentOutputError(
                f"Agent 1 semantic validation failed: {case['id']} field {field_name} must use priority outside enum."
            )


def _case_mentions_invalid_boundary(case: dict[str, Any], requirement_name: str) -> bool:
    text = _normalise_text(_case_text(case))
    if requirement_name not in text:
        return False
    return any(marker in text for marker in ("menor", "maior", "curt", "long", "inval"))


def _case_text(case: dict[str, Any]) -> str:
    return json.dumps(case, ensure_ascii=False)


def _criterion_text(criterion: dict[str, Any]) -> str:
    return " ".join(str(value) for value in criterion.values())


def _normalise_text(text: str) -> str:
    replacements = str.maketrans(
        {"á": "a", "à": "a", "ã": "a", "â": "a", "é": "e", "ê": "e", "í": "i", "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ç": "c"}
    )
    return text.lower().translate(replacements)


def _has_exact_total_evidence(context_text: str, number: str) -> bool:
    evidence_patterns = (
        rf"\btotal\s*[=:]\s*{re.escape(number)}\b",
        rf"\bquantidade\s*[=:]\s*{re.escape(number)}\b",
        rf"\bowns\s+{re.escape(number)}\s+requests\b",
        rf"\b{re.escape(number)}\s+solicitacoes\b",
        rf"\b{re.escape(number)}\s+requests\b",
        rf"\bitems\s*=\s*\[\]\s*e\s*total\s*=\s*{re.escape(number)}\b",
    )
    return any(re.search(pattern, context_text) for pattern in evidence_patterns)


def _to_output(data: dict[str, Any], response: LLMResponse) -> GenerationOutput:
    return GenerationOutput(
        test_cases=[TestCase(**case) for case in data["test_cases"]],
        matriz_rastreabilidade=data["matriz_rastreabilidade"],
        alertas=data["alertas"],
        raw_response=response,
    )


def output_to_json(output: GenerationOutput) -> str:
    return json.dumps(output.to_dict(), ensure_ascii=False, indent=2)
