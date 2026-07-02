from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class UserStory:
    id: str
    title: str
    persona: str
    acao: str
    beneficio: str
    acceptance_criteria: list[dict[str, str]]
    touched_screens: list[str] = field(default_factory=list)
    touched_endpoints: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "UserStory":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(
            id=str(data["id"]).strip(),
            title=str(data["title"]).strip(),
            persona=str(data.get("persona", "")).strip(),
            acao=str(data.get("acao", "")).strip(),
            beneficio=str(data.get("beneficio", "")).strip(),
            acceptance_criteria=list(data.get("acceptance_criteria", [])),
            touched_screens=list(data.get("touched_screens", [])),
            touched_endpoints=list(data.get("touched_endpoints", [])),
        )


@dataclass
class ContextSection:
    title: str
    body: str

    def render(self) -> str:
        return f"## {self.title}\n\n{self.body.rstrip()}\n"


@dataclass
class ContextBlob:
    story_id: str
    story: UserStory
    sections: list[ContextSection]

    def _header(self) -> str:
        return (
            f"# Contexto para {self.story.id} — {self.story.title}\n\n"
            "> Este bloco é injetado nos prompts dos agentes 0–3 e do Sumarizador "
            "como verdade de referência sobre o domínio, a API, a UI e o formato "
            "esperado de saída. Não inventar fatos fora deste contexto.\n"
        )

    @property
    def text(self) -> str:
        return self._header() + "\n".join(s.render() for s in self.sections)

    def filtered_text(self, exclude: set[str]) -> str:
        """Render sections excluding the named ones (used to avoid duplicate injection)."""
        sections = [s for s in self.sections if s.title not in exclude]
        return self._header() + "\n".join(s.render() for s in sections)

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def token_estimate(self) -> int:
        # PT-BR prose mixed with code runs ~3–3.5 chars/token; use 3.5 to avoid
        # underestimating context budget for downstream agents.
        return int(self.char_count / 3.5)

    def section_titles(self) -> list[str]:
        return [s.title for s in self.sections]
