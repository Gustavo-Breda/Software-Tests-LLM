# Phase 5 — Agent 3: Selenium/PyTest Code Generation
#
# Recebe os casos de teste aprovados (Agent 1/2) e gera três arquivos Python
# prontos para execução com PyTest + Selenium.
#
# Regras obrigatórias de geração (PLAN.md §7 e AGENTS.md):
#   - Page Object Model: cada tela é uma classe em pages.py; ZERO seletores
#     raw dentro das funções de teste.
#   - Seletores: preferir data-testid (de pipeline/context/ui_map.json);
#     só cair em CSS/XPath se o seletor não estiver documentado — nesse caso
#     registrar em pendencias_de_automacao.
#   - Sem time.sleep() — usar WebDriverWait com condições explícitas.
#   - Uma função por caso: test_{id}_{descricao_curta}
#     com comentário indicando o ID e objetivo do caso.
#   - Dados de teste vindos de fixtures/JSON, nunca hardcoded na função.
#
# Prompt : pipeline/prompts/05_codegen.txt
# Schema : pipeline/schemas/agent3_out.json
#
# Contrato de saída (PLAN.md §7):
#   {
#     "arquivos": {
#       "conftest.py": "...código...",
#       "pages.py":    "...código...",
#       "test_us_XX.py": "...código..."
#     },
#     "pendencias_de_automacao": [
#       "Seletor do botão X não documentado em ui_map — automatização parcial"
#     ]
#   }

from dataclasses import dataclass, field
from pathlib import Path

from ..llm.adapter import LLMClient, LLMResponse
from ..context.context_builder import ContextBlob
from .agent1_generate import GenerationOutput


@dataclass
class CodegenOutput:
    arquivos: dict[str, str] = field(default_factory=dict)
    # keys esperadas: "conftest.py", "pages.py", "test_us_XX.py"
    pendencias_de_automacao: list[str] = field(default_factory=list)
    raw_response: LLMResponse | None = None


def run(blob: ContextBlob, generation: GenerationOutput, client: LLMClient) -> CodegenOutput:
    # TODO(Phase 5):
    # 1. Carregar pipeline/prompts/05_codegen.txt
    # 2. Injetar blob.text + test_cases aprovados (JSON) + seletores do ui_map no prompt
    #    — os seletores já estão no blob, mas pode ser útil destacá-los separadamente
    # 3. Chamar client.complete(prompt, system=..., temperature=0.1)
    #    (temperatura baixa para código — menos criatividade, mais consistência)
    # 4. Parsear JSON da resposta (os arquivos são strings de código dentro do JSON)
    # 5. Validar contra pipeline/schemas/agent3_out.json
    # 6. Checar que pages.py não contém seletores hardcoded fora de constantes de classe
    # 7. Checar que nenhum arquivo contém time.sleep()
    # 8. Retornar CodegenOutput
    raise NotImplementedError("Phase 5")


def save_to_disk(output: CodegenOutput, dest: Path) -> None:
    # TODO(Phase 5):
    # Salvar cada arquivo de output.arquivos em generated/scripts/<story_id>/
    # Criar o diretório se não existir.
    # Gravar pendencias_de_automacao em generated/scripts/<story_id>/pendencias.txt
    raise NotImplementedError("Phase 5")
