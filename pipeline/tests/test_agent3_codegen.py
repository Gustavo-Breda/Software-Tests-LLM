import json

import pytest

from pipeline.agents import agent3_codegen
from pipeline.agents.agent1_generate import GenerationOutput, TestCase
from pipeline.agents.utils import AgentOutputError
from pipeline.context import ContextBuilder
from pipeline.llm.adapter import LLMClient, LLMResponse


class FakeClient(LLMClient):
    provider = "fake"

    def __init__(self, text: str) -> None:
        super().__init__("fake-model")
        self.text = text
        self.prompts: list[str] = []

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.prompts.append(prompt)
        return LLMResponse(text=self.text, model=self.model, provider=self.provider)


def _blob():
    return ContextBuilder.from_repo().build("US-01")


def _generation() -> GenerationOutput:
    return GenerationOutput(
        test_cases=[
            TestCase(
                id="TC-01-01",
                titulo="Login bem-sucedido",
                objetivo="Validar login com credenciais corretas.",
                criterios_cobertos=["CA-01.1"],
                tipo="positivo",
                prioridade="alta",
                pre_condicoes=[],
                dados_de_teste={"email": "alice@example.com", "password": "Senha123"},
                passos=["Acessar /login.", "Entrar com credenciais válidas."],
                resultado_esperado="Redireciona para /requests.",
                automatizavel=True,
            )
        ],
        matriz_rastreabilidade=[{"criterio": "CA-01.1", "casos": ["TC-01-01"]}],
        alertas=[],
    )


def _valid_payload() -> dict:
    return {
        "arquivos": {
            "conftest.py": (
                "import pytest\n\n"
                "@pytest.fixture\n"
                "def login_data():\n"
                "    return {'email': 'alice@example.com', 'password': 'Senha123'}\n"
            ),
            "pages.py": (
                "from selenium.webdriver.common.by import By\n\n"
                "class LoginPage:\n"
                "    EMAIL = (By.CSS_SELECTOR, '[data-testid=login-email]')\n"
                "    PASSWORD = (By.CSS_SELECTOR, '[data-testid=login-password]')\n"
                "    SUBMIT = (By.CSS_SELECTOR, '[data-testid=login-submit]')\n"
            ),
            "test_us_01.py": (
                "def test_tc_01_01_login_bem_sucedido(login_data):\n"
                "    # TC-01-01: Validar login com credenciais corretas.\n"
                "    assert login_data['email'] == 'alice@example.com'\n"
            ),
        },
        "pendencias_de_automacao": [],
    }


def test_agent3_accepts_valid_codegen_json():
    client = FakeClient(json.dumps(_valid_payload()))

    output = agent3_codegen.run(_blob(), _generation(), client)

    assert sorted(output.arquivos) == ["conftest.py", "pages.py", "test_us_01.py"]
    assert output.pendencias_de_automacao == []
    assert "{approved_test_cases_json}" not in client.prompts[0]
    assert "{ui_map_json}" not in client.prompts[0]


def test_agent3_rejects_time_sleep():
    payload = _valid_payload()
    payload["arquivos"]["pages.py"] += "\nimport time\ntime.sleep(1)\n"
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="time.sleep"):
        agent3_codegen.run(_blob(), _generation(), client)


def test_agent3_rejects_selector_inside_test_file():
    payload = _valid_payload()
    payload["arquivos"]["test_us_01.py"] += "\nRAW = '[data-testid=login-email]'\n"
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="embeds selectors"):
        agent3_codegen.run(_blob(), _generation(), client)


def test_agent3_rejects_missing_case_function():
    payload = _valid_payload()
    payload["arquivos"]["test_us_01.py"] = "def test_other(login_data):\n    assert login_data\n"
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="missing test function"):
        agent3_codegen.run(_blob(), _generation(), client)


def test_agent3_rejects_extra_test_file():
    payload = _valid_payload()
    payload["arquivos"]["test_extra.py"] = "def test_extra():\n    assert True\n"
    client = FakeClient(json.dumps(payload))

    with pytest.raises(AgentOutputError, match="expected only"):
        agent3_codegen.run(_blob(), _generation(), client)
