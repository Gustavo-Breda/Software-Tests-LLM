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
#       "cobertura": 0.0–1.0,
#       "fidelidade_ao_requisito": 0.0–1.0,
#       "clareza": 0.0–1.0,
#       "automatizabilidade": 0.0–1.0
#     },
#     "casos_aprovados": ["TC-XX-YY", ...],
#     "casos_reprovados": ["TC-XX-ZZ", ...],
#     "problemas": ["..."],
#     "cenarios_omitidos_sugeridos": ["..."],
#     "decisao": "APROVADO" | "REPROVADO"
#   }
#
# Estratégia de avaliação (evitar viés):
#   - Pontuar por DIMENSÃO, não só pass/fail global — juiz que só reprova tudo
#     tem viés de estilo; medir judge precision/recall vs. oráculo humano (Phase 7).
#   - Estratificar por tipo (positivo / negativo / borda) para que casos positivos
#     fáceis não inflacionem o score (cf. Qin et al. DAJ, PLAN.md §8).

from dataclasses import dataclass, field
from typing import Any
import json

from ..llm.adapter import LLMClient, LLMResponse
from ..context.context_builder import ContextBlob
from .agent1_generate import GenerationOutput, run as agent1_run

_MAX_REPAIR_ITERATIONS = 3   # N=3, definido em PLAN.md §3.3


@dataclass
class JudgeScore:
    cobertura: float
    fidelidade_ao_requisito: float
    clareza: float
    automatizabilidade: float


@dataclass
class JudgeOutput:
    status_geral: str                               # "APROVADO" | "REPROVADO"
    pontuacao: JudgeScore
    casos_aprovados: list[str] = field(default_factory=list)
    casos_reprovados: list[str] = field(default_factory=list)
    problemas: list[str] = field(default_factory=list)
    cenarios_omitidos_sugeridos: list[str] = field(default_factory=list)
    decisao: str = "REPROVADO"
    repair_attempts: int = 0                        # quantas vezes o repair rodou
    raw_response: LLMResponse | None = None


def _call_judge(blob: ContextBlob, generation: GenerationOutput, client: LLMClient) -> JudgeOutput:
    # TODO(Phase 4):
    # 1. Carregar pipeline/prompts/03_judge.txt
    # 2. Injetar blob.text + JSON dos test_cases no prompt
    # 3. Chamar client.complete(prompt, system=..., temperature=0.2)
    # 4. Parsear JSON da resposta
    # 5. Validar contra pipeline/schemas/agent2_out.json
    # 6. Retornar JudgeOutput
    raise NotImplementedError("Phase 4")


def run(blob: ContextBlob, generation: GenerationOutput, client: LLMClient) -> JudgeOutput:
    attempt = 0
    current_gen = generation

    while attempt < _MAX_REPAIR_ITERATIONS:
        result = _call_judge(blob, current_gen, client)
        result.repair_attempts = attempt

        if result.decisao == "APROVADO":
            return result

        attempt += 1
        if attempt >= _MAX_REPAIR_ITERATIONS:
            # esgotou retries — retornar o melhor resultado obtido
            return result

        # TODO(Phase 4): montar feedback do juiz como string estruturada
        # e passar para agent1_run com repair_feedback
        feedback = _build_repair_feedback(result)
        current_gen = agent1_run(blob, client, repair_feedback=feedback)

    return result   # unreachable, mas satisfaz o type checker


def _build_repair_feedback(judge: JudgeOutput) -> str:
    # TODO(Phase 4): serializar problemas + casos_reprovados + sugestões
    # em linguagem natural (ou JSON) para injetar no prompt 04_repair.txt
    raise NotImplementedError("Phase 4")
