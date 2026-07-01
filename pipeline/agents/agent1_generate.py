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
# Contrato (PLAN.md §7):
#   {
#     "test_cases": [{
#       "id": "TC-XX-YY",
#       "titulo": "...",
#       "objetivo": "...",
#       "criterios_cobertos": ["CA-XX.Y"],
#       "tipo": "positivo" | "negativo" | "borda",
#       "prioridade": "alta" | "média" | "baixa",
#       "pre_condicoes": ["..."],
#       "dados_de_teste": {},
#       "passos": ["..."],
#       "resultado_esperado": "...",
#       "automatizavel": true | false,
#       "observacoes": "..."
#     }],
#     "matriz_rastreabilidade": [{"criterio": "CA-XX.Y", "casos": ["TC-XX-YY"]}],
#     "alertas": ["..."]
#   }

from dataclasses import dataclass, field
from typing import Any

from ..llm.adapter import LLMClient, LLMResponse
from ..context.context_builder import ContextBlob


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


def run(blob: ContextBlob, client: LLMClient, *, repair_feedback: str | None = None) -> GenerationOutput:
    # TODO(Phase 3):
    # 1. Escolher prompt:
    #    - Se repair_feedback is None → pipeline/prompts/02_generate.txt
    #    - Se repair_feedback not None → pipeline/prompts/04_repair.txt
    #      (injetar feedback do juiz para que o modelo corrija os casos reprovados)
    # 2. Injetar blob.text + story JSON no prompt
    # 3. Chamar client.complete(prompt, system=..., temperature=0.2)
    # 4. Parsear JSON da resposta
    # 5. Validar contra pipeline/schemas/agent1_out.json
    # 6. Garantir que todo test_case.criterios_cobertos referencia um CA real da story
    # 7. Retornar GenerationOutput
    raise NotImplementedError("Phase 3")
