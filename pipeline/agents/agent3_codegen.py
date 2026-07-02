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

import ast
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..llm.adapter import LLMClient, LLMResponse
from ..context import ContextBlob
from .agent1_generate import GenerationOutput
from .utils import AgentOutputError, REPO_ROOT, extract_json_object, load_prompt, validate_schema


_SYSTEM_PROMPT = (
    "Você responde apenas com JSON válido e segue estritamente o contrato solicitado."
)
_ALLOWED_STATIC_FILES = {"conftest.py", "pages.py"}
_TEST_FILE_PATTERN = re.compile(r"^test_[a-zA-Z0-9_]+\.py$")
_TESTID_PATTERN = re.compile(r"data-testid\s*=\s*[\"']?([a-zA-Z0-9_-]+)")


@dataclass
class CodegenOutput:
    arquivos: dict[str, str] = field(default_factory=dict)
    # keys esperadas: "conftest.py", "pages.py", "test_us_XX.py"
    pendencias_de_automacao: list[str] = field(default_factory=list)
    raw_response: LLMResponse | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw_response", None)
        return data


def run(blob: ContextBlob, generation: GenerationOutput, client: LLMClient) -> CodegenOutput:
    print(f"[agent3] start story={blob.story_id} cases={len(generation.test_cases)}")
    prompt = _build_prompt(blob, generation)
    response = client.complete(
        prompt,
        system=_SYSTEM_PROMPT,
        temperature=0.1,
        max_tokens=8192,
    )
    data = extract_json_object(response.text)
    validate_schema(data, "agent3_out.json")
    _validate_semantics(blob, generation, data)
    output = CodegenOutput(
        arquivos=data["arquivos"],
        pendencias_de_automacao=data["pendencias_de_automacao"],
        raw_response=response,
    )
    print(
        f"[agent3] done story={blob.story_id} files={len(output.arquivos)} "
        f"pending={len(output.pendencias_de_automacao)} "
        f"latency={response.latency_seconds:.2f}s"
    )
    return output


def save_to_disk(output: CodegenOutput, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for filename, content in output.arquivos.items():
        (dest / filename).write_text(content.rstrip() + "\n", encoding="utf-8")
    (dest / "pendencias_de_automacao.json").write_text(
        json.dumps(output.pendencias_de_automacao, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _build_prompt(blob: ContextBlob, generation: GenerationOutput) -> str:
    prompt = load_prompt("05_codegen.txt")
    replacements = {
        "system_context": blob.text,
        "ui_map_json": _load_ui_map_json(),
        "story_id": blob.story_id,
        "approved_test_cases_json": json.dumps(
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


def _load_ui_map_json() -> str:
    path = REPO_ROOT / "pipeline" / "context" / "ui_map.json"
    return json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)


def _validate_semantics(
    blob: ContextBlob,
    generation: GenerationOutput,
    data: dict[str, Any],
) -> None:
    files = data["arquivos"]
    filenames = set(files)
    expected_test_file = f"test_{blob.story_id.lower().replace('-', '_')}.py"

    unknown_files = [
        filename
        for filename in filenames
        if filename not in _ALLOWED_STATIC_FILES and not _TEST_FILE_PATTERN.match(filename)
    ]
    if unknown_files:
        raise AgentOutputError(
            f"Agent 3 semantic validation failed: unsupported file names {sorted(unknown_files)}."
        )
    if expected_test_file not in filenames:
        raise AgentOutputError(
            f"Agent 3 semantic validation failed: missing expected test file {expected_test_file}."
        )
    test_files = sorted(filename for filename in filenames if filename.startswith("test_"))
    if test_files != [expected_test_file]:
        raise AgentOutputError(
            f"Agent 3 semantic validation failed: expected only {expected_test_file}, got {test_files}."
        )

    for filename, content in files.items():
        if "time.sleep(" in content:
            raise AgentOutputError(
                f"Agent 3 semantic validation failed: {filename} uses time.sleep()."
            )
        _parse_python(filename, content)

    _validate_test_functions(generation, files[expected_test_file])
    _validate_test_files_do_not_embed_selectors(files)
    _validate_selectors_are_documented(files, _documented_testids())


def _parse_python(filename: str, content: str) -> ast.Module:
    try:
        return ast.parse(content, filename=filename)
    except SyntaxError as exc:
        raise AgentOutputError(
            f"Agent 3 semantic validation failed: {filename} has invalid Python syntax: {exc.msg}."
        ) from exc


def _validate_test_functions(generation: GenerationOutput, test_file: str) -> None:
    module = _parse_python("generated test file", test_file)
    test_names = {
        node.name
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }
    for case in generation.test_cases:
        if not case.automatizavel:
            continue
        case_token = case.id.lower().replace("-", "_")
        if not any(case_token in name for name in test_names):
            raise AgentOutputError(
                f"Agent 3 semantic validation failed: missing test function for {case.id}."
            )


def _validate_test_files_do_not_embed_selectors(files: dict[str, str]) -> None:
    for filename, content in files.items():
        if not filename.startswith("test_"):
            continue
        if "data-testid" in content or "By." in content:
            raise AgentOutputError(
                f"Agent 3 semantic validation failed: {filename} embeds selectors outside pages.py."
            )


def _validate_selectors_are_documented(files: dict[str, str], documented: set[str]) -> None:
    used = set()
    for content in files.values():
        used.update(_TESTID_PATTERN.findall(content))
    undocumented = sorted(used - documented)
    if undocumented:
        raise AgentOutputError(
            "Agent 3 semantic validation failed: undocumented data-testid selectors "
            f"{undocumented}."
        )


def _documented_testids() -> set[str]:
    ui_map = json.loads((REPO_ROOT / "pipeline" / "context" / "ui_map.json").read_text(encoding="utf-8"))
    testids: set[str] = set()
    for screen in ui_map.get("screens", {}).values():
        for selector in screen.get("selectors", {}).values():
            match = _TESTID_PATTERN.search(str(selector))
            if match:
                testids.add(match.group(1))
    return testids
