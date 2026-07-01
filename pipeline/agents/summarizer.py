# Phase 6 — Summarization Agent
#
# Recebe o output do PyTest (stdout/stderr/JSON report) + logs do Selenium
# e produz um relatório estruturado classificando falhas e calculando cobertura
# por critério de aceitação.
#
# Categorias de falha (para o LLM classificar cada teste que falhou):
#   "sistema"    — bug real no app (o teste está correto)
#   "teste"      — o script de teste está errado (seletor, lógica, dado)
#   "seletor"    — seletor quebrou (UI mudou, data-testid removido)
#   "dado"       — problema com fixtures ou seed data
#   "ambiente"   — falha de infra (timeout de container, rede, Selenium)
#
# Prompt : pipeline/prompts/06_summarize.txt
# Schema : pipeline/schemas/summarizer_out.json
#
# Contrato de saída (PLAN.md §7):
#   {
#     "resumo": {
#       "total_casos": 0,
#       "aprovados": 0,
#       "reprovados": 0,
#       "taxa_execucao": 0.0
#     },
#     "falhas": [{
#       "caso_id": "TC-XX-YY",
#       "categoria": "sistema" | "teste" | "seletor" | "dado" | "ambiente",
#       "descricao": "...",
#       "evidencia": "trecho do log relevante"
#     }],
#     "cobertura_por_criterio": [{
#       "criterio_id": "CA-XX.Y",
#       "coberto": true | false,
#       "casos_associados": ["TC-XX-YY"]
#     }],
#     "alertas_de_qualidade": ["..."],
#     "proximos_passos": ["..."]
#   }

from dataclasses import dataclass, field
from typing import Any

from ..llm.adapter import LLMClient, LLMResponse


@dataclass
class FailureSummary:
    caso_id: str
    categoria: str      # "sistema" | "teste" | "seletor" | "dado" | "ambiente"
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


def run(pytest_output: str, selenium_logs: str, client: LLMClient) -> SummarizerOutput:
    # TODO(Phase 6):
    # 1. Carregar pipeline/prompts/06_summarize.txt
    # 2. Injetar pytest_output + selenium_logs (truncar se muito longos — risco de
    #    extrapolar contexto; priorizar stderr e falhas sobre stdout de testes ok)
    # 3. Chamar client.complete(prompt, system=..., temperature=0.2)
    # 4. Parsear JSON da resposta
    # 5. Validar contra pipeline/schemas/summarizer_out.json
    # 6. Calcular taxa_execucao = aprovados / total_casos
    # 7. Para cada criterio da story, verificar se há ao menos 1 caso aprovado associado
    # 8. Retornar SummarizerOutput
    raise NotImplementedError("Phase 6")


def save_report(output: SummarizerOutput, dest_path: str) -> None:
    # TODO(Phase 6):
    # Salvar o relatório como JSON em generated/reports/<story_id>_report.json
    raise NotImplementedError("Phase 6")
