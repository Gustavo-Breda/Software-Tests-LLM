# Phase 3 — Agent 0: Story Quality Gate
#
# Avalia a user story e os critérios de aceitação ANTES de qualquer geração.
# Retorna APROVADA ou PRECISA_DE_ESCLARECIMENTO com problemas detalhados.
# Rubrica: critérios INVEST (Hernández-Agüero et al.) — Independent, Negotiable,
# Valuable, Estimable, Small, Testable.
#
# Prompt : pipeline/prompts/01_quality_gate.txt
# Schema : pipeline/schemas/agent0_out.json
# Contrato (PLAN.md §7):
#   {
#     "status": "APROVADA" | "PRECISA_DE_ESCLARECIMENTO",
#     "derivavel": true | false,
#     "observacao_formato": "...",
#     "problemas": ["..."],
#     "recomendacao": "..."
#   }

from dataclasses import dataclass, field
from pathlib import Path

from ..llm.adapter import LLMClient, LLMResponse
from ..context.context_builder import ContextBlob


@dataclass
class QualityGateOutput:
    status: str                         # "APROVADA" | "PRECISA_DE_ESCLARECIMENTO"
    derivavel: bool
    observacao_formato: str
    problemas: list[str] = field(default_factory=list)
    recomendacao: str = ""
    raw_response: LLMResponse | None = None


def run(blob: ContextBlob, client: LLMClient) -> QualityGateOutput:
    # TODO(Phase 3):
    # 1. Carregar pipeline/prompts/01_quality_gate.txt
    # 2. Injetar blob.text no prompt
    # 3. Chamar client.complete(prompt, system=..., temperature=0.2)
    # 4. Parsear JSON da resposta
    # 5. Validar contra pipeline/schemas/agent0_out.json
    # 6. Retornar QualityGateOutput
    # Se status == "PRECISA_DE_ESCLARECIMENTO", o runner devolve para o humano refinar.
    raise NotImplementedError("Phase 3")
