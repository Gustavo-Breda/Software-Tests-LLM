# Phase 4 — Agent 2: LLM-as-a-Judge + Repair Loop
#
# Avalia os casos gerados pelo Agent 1 em quatro dimensões e decide se o
# batch inteiro está APROVADO ou REPROVADO. Casos reprovados voltam para o
# Agent 1 via repair branch (prompt 04_repair.txt), limitado a N=3 tentativas.
#
# O repair loop fica aqui (não no runner) para manter o estado de tentativas
# encapsulado. O runner só chama judge(blob, cases, client) e recebe o resultado final.
#
# Prompt avaliação : pipeline/prompts/03_judge.txt
# Prompt reparo    : pipeline/prompts/04_repair.txt  (repassado ao Agent 1)
# Schema           : pipeline/schemas/agent2_out.json
#
# Contrato de saída (PLAN.md §7):
#   {
#     "status_geral": "APROVADO" | "REPROVADO",
#     "pontuacao": {
#       "cobertura": 0-10,
#       "fidelidade_ao_requisito": 0-10,
#       "clareza": 0-10,
#       "automatizabilidade": 0-10
#     },
#     "casos_aprovados": ["TC-XX-YY", ...],
#     "casos_reprovados": ["TC-XX-ZZ", ...],
#     "problemas": [{...}],
#     "cenarios_omitidos_sugeridos": [{...}],
#     "decisao": "APROVADO" | "REPROVADO"
#   }
#
# Estratégia de avaliação (evitar viés):
#   - Pontuar por DIMENSÃO, não só pass/fail global — juiz que só reprova tudo
#     tem viés de estilo; medir judge precision/recall vs. oráculo humano (Phase 7).
#   - Estratificar por tipo (positivo / negativo / borda) para que casos positivos
#     fáceis não inflacionem o score (cf. Qin et al. DAJ, PLAN.md §8).

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from ..llm.adapter import LLMClient, LLMResponse
from ..context import ContextBlob
from .agent1_generate import GenerationOutput, run as agent1_run
from .utils import AgentOutputError, extract_json_object, load_prompt, validate_schema

_MAX_REPAIR_ATTEMPTS = 3
_SYSTEM_PROMPT = (
    "Você responde apenas com JSON válido e segue estritamente o contrato solicitado."
)


@dataclass
class JudgeScore:
    cobertura: int
    fidelidade_ao_requisito: int
    clareza: int
    automatizabilidade: int


@dataclass
class JudgeProblem:
    caso_de_teste: str
    tipo: str
    descricao: str
    evidencia_na_historia: str
    acao_recomendada: str


@dataclass
class OmittedScenario:
    descricao: str
    criterio_relacionado: str
    justificativa: str
    tipo_sugerido: str


@dataclass
class JudgeOutput:
    status_geral: str
    pontuacao: JudgeScore
    casos_aprovados: list[str] = field(default_factory=list)
    casos_reprovados: list[str] = field(default_factory=list)
    problemas: list[JudgeProblem] = field(default_factory=list)
    cenarios_omitidos_sugeridos: list[OmittedScenario] = field(default_factory=list)
    decisao: str = "REPROVADO"
    raw_response: LLMResponse | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw_response", None)
        return data


@dataclass
class RepairGeneration:
    attempt: int
    output: GenerationOutput


@dataclass
class JudgeRunResult:
    final_output: JudgeOutput
    final_generation: GenerationOutput
    attempt_reports: list[JudgeOutput] = field(default_factory=list)
    repair_generations: list[RepairGeneration] = field(default_factory=list)
    repair_attempts: int = 0
    rejected_after_repair: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": self.final_output.to_dict(),
            "repair_attempts": self.repair_attempts,
            "rejected_after_repair": self.rejected_after_repair,
        }


def _call_judge(blob: ContextBlob, generation: GenerationOutput, client: LLMClient) -> JudgeOutput:
    print(
        f"[agent2] judge start story={blob.story_id} cases={len(generation.test_cases)}"
    )
    prompt = _build_prompt(blob, generation)
    response = client.complete(
        prompt,
        system=_SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=4096,
    )
    data = extract_json_object(response.text)
    validate_schema(data, "agent2_out.json")
    _validate_semantics(blob, generation, data)
    output = _to_output(data, response)
    print(
        f"[agent2] judge done story={blob.story_id} decisao={output.decisao} "
        f"approved={len(output.casos_aprovados)} rejected={len(output.casos_reprovados)} "
        f"problems={len(output.problemas)} omitted={len(output.cenarios_omitidos_sugeridos)} "
        f"latency={response.latency_seconds:.2f}s"
    )
    return output


def run(blob: ContextBlob, generation: GenerationOutput, client: LLMClient) -> JudgeRunResult:
    print(f"[agent2] run start story={blob.story_id}")
    attempt = 0
    current_gen = generation
    attempt_reports: list[JudgeOutput] = []
    repair_generations: list[RepairGeneration] = []

    while True:
        print(f"[agent2] attempt={attempt} story={blob.story_id}")
        result = _call_judge(blob, current_gen, client)
        attempt_reports.append(result)

        if result.decisao == "APROVADO":
            print(f"[agent2] approved story={blob.story_id} attempt={attempt}")
            return JudgeRunResult(
                final_output=result,
                final_generation=current_gen,
                attempt_reports=attempt_reports,
                repair_generations=repair_generations,
                repair_attempts=attempt,
            )

        if attempt >= _MAX_REPAIR_ATTEMPTS:
            print(f"[agent2] rejected_after_repair story={blob.story_id} attempts={attempt}")
            return JudgeRunResult(
                final_output=result,
                final_generation=current_gen,
                attempt_reports=attempt_reports,
                repair_generations=repair_generations,
                repair_attempts=attempt,
                rejected_after_repair=True,
            )

        feedback = _build_repair_feedback(result)
        attempt += 1
        print(f"[agent2] repair start story={blob.story_id} attempt={attempt}")
        current_gen = agent1_run(
            blob,
            client,
            repair_feedback=feedback,
            current_generation=current_gen,
        )
        repair_generations.append(RepairGeneration(attempt=attempt, output=current_gen))
        print(
            f"[agent2] repair done story={blob.story_id} attempt={attempt} "
            f"cases={len(current_gen.test_cases)}"
        )


def _build_repair_feedback(judge: JudgeOutput) -> str:
    return json.dumps(judge.to_dict(), ensure_ascii=False, indent=2)


def _build_prompt(blob: ContextBlob, generation: GenerationOutput) -> str:
    prompt = load_prompt("03_judge.txt")
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
        "user_story": json.dumps(story_payload, ensure_ascii=False, indent=2),
        "acceptance_criteria": json.dumps(
            story.acceptance_criteria,
            ensure_ascii=False,
            indent=2,
        ),
        "system_context": blob.text,
        "generated_test_cases_json": json.dumps(
            generation.to_dict(),
            ensure_ascii=False,
            indent=2,
        ),
    }
    for key, value in replacements.items():
        placeholder = "{" + key + "}"
        if placeholder not in prompt:
            raise AgentOutputError(f"Missing prompt placeholder: {placeholder}")
        prompt = prompt.replace(placeholder, value)
    return prompt


def _validate_semantics(
    blob: ContextBlob,
    generation: GenerationOutput,
    data: dict[str, Any],
) -> None:
    valid_case_ids = {case.id for case in generation.test_cases}
    valid_criteria = {
        str(criterion.get("id"))
        for criterion in blob.story.acceptance_criteria
        if criterion.get("id")
    }
    approved = set(data["casos_aprovados"])
    rejected = set(data["casos_reprovados"])

    if approved - valid_case_ids:
        raise AgentOutputError(
            f"Agent 2 semantic validation failed: unknown approved case IDs {sorted(approved - valid_case_ids)}."
        )
    if rejected - valid_case_ids:
        raise AgentOutputError(
            f"Agent 2 semantic validation failed: unknown rejected case IDs {sorted(rejected - valid_case_ids)}."
        )
    if approved & rejected:
        raise AgentOutputError(
            "Agent 2 semantic validation failed: same case cannot be both approved and rejected."
        )
    if data["status_geral"] != data["decisao"]:
        raise AgentOutputError(
            "Agent 2 semantic validation failed: status_geral must match decisao."
        )

    problems = data["problemas"]
    omitted = data["cenarios_omitidos_sugeridos"]
    if data["decisao"] == "APROVADO":
        if rejected or problems or omitted:
            raise AgentOutputError(
                "Agent 2 semantic validation failed: APROVADO must not contain rejected cases, problems, or omitted scenarios."
            )
    else:
        if not (rejected or problems or omitted):
            raise AgentOutputError(
                "Agent 2 semantic validation failed: REPROVADO must include rejected cases, problems, or omitted scenarios."
            )

    for problem in problems:
        case_id = problem["caso_de_teste"]
        if case_id != "GERAL" and case_id not in valid_case_ids:
            raise AgentOutputError(
                f"Agent 2 semantic validation failed: unknown problem case ID {case_id}."
            )

    for scenario in omitted:
        criterion_id = scenario["criterio_relacionado"]
        if criterion_id not in valid_criteria:
            raise AgentOutputError(
                f"Agent 2 semantic validation failed: unknown omitted criterion {criterion_id}."
            )


def _to_output(data: dict[str, Any], response: LLMResponse) -> JudgeOutput:
    return JudgeOutput(
        status_geral=data["status_geral"],
        pontuacao=JudgeScore(**data["pontuacao"]),
        casos_aprovados=data["casos_aprovados"],
        casos_reprovados=data["casos_reprovados"],
        problemas=[JudgeProblem(**problem) for problem in data["problemas"]],
        cenarios_omitidos_sugeridos=[
            OmittedScenario(**scenario) for scenario in data["cenarios_omitidos_sugeridos"]
        ],
        decisao=data["decisao"],
        raw_response=response,
    )
