import json
from pathlib import Path
from typing import Any

from .models import UserStory, ContextSection, ContextBlob


REQUIRED_SECTIONS: tuple[str, ...] = (
    "Glossário de Domínio",
    "Contrato da API (endpoints relevantes)",
    "Mapa de UI (telas relevantes)",
    "Dados de seed disponíveis",
    "Exemplo aprovado (referência de formato)",
    "História do Usuário e Critérios de Aceitação",
)


class ContextBuilder:
    def __init__(
        self,
        *,
        glossary_path: Path,
        ui_map_path: Path,
        examples_dir: Path,
        stories_dir: Path,
    ) -> None:
        if not glossary_path.is_file():
            raise FileNotFoundError(f"Glossário não encontrado: {glossary_path}")
        if not ui_map_path.is_file():
            raise FileNotFoundError(f"ui_map.json não encontrado: {ui_map_path}")
        if not stories_dir.is_dir():
            raise FileNotFoundError(f"Diretório de stories não encontrado: {stories_dir}")

        self._glossary_text: str = glossary_path.read_text(encoding="utf-8")
        self._ui_map: dict[str, Any] = json.loads(ui_map_path.read_text(encoding="utf-8"))
        self._examples_dir = examples_dir
        self._stories_dir = stories_dir

    @classmethod
    def from_repo(cls, repo_root: Path | None = None) -> "ContextBuilder":
        if repo_root is None:
            # parents[0]=context, parents[1]=pipeline, parents[2]=repo_root
            repo_root = Path(__file__).resolve().parents[2]
        return cls(
            glossary_path=repo_root / "pipeline" / "context" / "glossary.md",
            ui_map_path=repo_root / "pipeline" / "context" / "ui_map.json",
            examples_dir=repo_root / "pipeline" / "context" / "examples",
            stories_dir=repo_root / "data" / "user_stories",
        )

    def list_stories(self) -> list[str]:
        return sorted(p.stem for p in self._stories_dir.glob("*.yaml"))

    def load_story(self, story_id: str) -> UserStory:
        path = self._stories_dir / f"{story_id}.yaml"
        if not path.is_file():
            available = ", ".join(self.list_stories()) or "(nenhuma)"
            raise FileNotFoundError(
                f"Story '{story_id}' não encontrada. Disponíveis: {available}"
            )
        return UserStory.from_yaml(path)

    def build(self, story: str | UserStory) -> ContextBlob:
        story_obj = self.load_story(story) if isinstance(story, str) else story
        sections = [
            ContextSection("Glossário de Domínio", self._render_glossary()),
            ContextSection(
                "Contrato da API (endpoints relevantes)",
                self._render_api(story_obj),
            ),
            ContextSection(
                "Mapa de UI (telas relevantes)",
                self._render_screens(story_obj),
            ),
            ContextSection("Dados de seed disponíveis", self._render_seed()),
            ContextSection(
                "Exemplo aprovado (referência de formato)",
                self._render_example(story_obj),
            ),
            ContextSection(
                "História do Usuário e Critérios de Aceitação",
                self._render_story(story_obj),
            ),
        ]
        return ContextBlob(story_id=story_obj.id, story=story_obj, sections=sections)

    def build_all(self) -> list[ContextBlob]:
        return [self.build(sid) for sid in self.list_stories()]

    def _render_glossary(self) -> str:
        # Strip the top-level "# Glossário..." header so it nests under our H2.
        lines = self._glossary_text.splitlines()
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
            while lines and not lines[0].strip():
                lines = lines[1:]
        return "\n".join(lines).strip()

    def _render_api(self, story: UserStory) -> str:
        endpoints = self._relevant_endpoints(story)
        if not endpoints:
            return "_Nenhum endpoint diretamente associado a esta story._"
        lines: list[str] = []
        for dotted, ep in endpoints.items():
            method = ep.get("method", "?")
            path = ep.get("path", "?")
            query = ep.get("query")
            line = f"- **`{method} {path}`** *(refª: `{dotted}`)*"
            if query:
                line += f" — query params: `{', '.join(query)}`"
            lines.append(line)
        base = self._ui_map.get("base_urls", {})
        if base:
            lines.append("")
            lines.append(
                f"_Base URLs: backend = `{base.get('backend', '?')}` · "
                f"frontend = `{base.get('frontend', '?')}`_"
            )
        return "\n".join(lines)

    def _render_screens(self, story: UserStory) -> str:
        screens = self._relevant_screens(story)
        if not screens:
            return "_Nenhuma tela diretamente associada a esta story._"
        chunks: list[str] = []
        for name, screen in screens.items():
            head = f"### Tela `{name}`"
            route = screen.get("route")
            if route:
                head += f" — rota `{route}`"
            chunks.append(head)
            selectors = screen.get("selectors", {})
            if selectors:
                for sel_name, sel_value in selectors.items():
                    chunks.append(f"- `{sel_name}` → `{sel_value}`")
            else:
                chunks.append("_(sem seletores documentados)_")
            chunks.append("")
        return "\n".join(chunks).rstrip()

    def _render_seed(self) -> str:
        users = self._ui_map.get("seed_users", [])
        if not users:
            return "_Sem usuários de seed documentados._"
        lines = []
        for u in users:
            email = u.get("email", "?")
            pwd = u.get("password", "?")
            note = u.get("note", "")
            lines.append(f"- **`{email}`** · senha: `{pwd}` — {note}")
        lines.append("")
        lines.append(
            "_O banco é recriado em todo start do backend "
            "(`RESET_DB_ON_STARTUP=1`). Testes não devem depender de estado "
            "acumulado entre execuções._"
        )
        return "\n".join(lines)

    def _render_example(self, story: UserStory) -> str:
        example = self._best_example(story)
        if example is None:
            return "_Nenhum exemplo aprovado disponível ainda._"
        # Strip _metadata before showing — it's curation info, not LLM input.
        public = {k: v for k, v in example.items() if not k.startswith("_")}
        pretty = json.dumps(public, indent=2, ensure_ascii=False)
        meta = example.get("_metadata", {})
        provenance = (
            f"_Story de origem: **{meta.get('story_id', '?')}** · "
            f"aprovado em {meta.get('approved_at', '?')} "
            f"por {meta.get('approved_by', '?')}._\n\n"
            "Use este exemplo como referência **somente para o formato de saída**. "
            "Os casos de teste a gerar devem ser específicos à story atual.\n\n"
        )
        return provenance + "```json\n" + pretty + "\n```"

    def _render_story(self, story: UserStory) -> str:
        lines = [
            f"**ID:** `{story.id}`",
            f"**Título:** {story.title}",
            "",
            f"Como **{story.persona}**, quero **{story.acao}**, "
            f"para que **{story.beneficio}**.",
            "",
            "### Critérios de Aceitação",
            "",
        ]
        for crit in story.acceptance_criteria:
            cid = crit.get("id", "?")
            ctype = crit.get("tipo", "")
            desc = " ".join(str(crit.get("description", "")).split())
            tag = f" *(tipo: {ctype})*" if ctype else ""
            lines.append(f"- **{cid}**{tag}: {desc}")
        return "\n".join(lines)

    def _relevant_endpoints(self, story: UserStory) -> dict[str, dict[str, Any]]:
        api = self._ui_map.get("api", {})
        wanted: set[str] = set(story.touched_endpoints or [])
        result: dict[str, dict[str, Any]] = {}
        for group_name, group in api.items():
            if not isinstance(group, dict):
                continue
            for ep_name, ep in group.items():
                if not isinstance(ep, dict):
                    continue
                dotted = f"{group_name}.{ep_name}"
                ep_story = ep.get("story")
                if ep_story == story.id or dotted in wanted:
                    result[dotted] = ep
        return result

    def _relevant_screens(self, story: UserStory) -> dict[str, dict[str, Any]]:
        screens = self._ui_map.get("screens", {})
        wanted: set[str] = set(story.touched_screens or [])
        result: dict[str, dict[str, Any]] = {}
        for name, screen in screens.items():
            if not isinstance(screen, dict):
                continue
            if screen.get("story") == story.id or name in wanted:
                result[name] = screen
        return result

    def _best_example(self, story: UserStory) -> dict[str, Any] | None:
        if not self._examples_dir.is_dir():
            return None
        files = sorted(self._examples_dir.glob("*.json"))
        same_story: dict[str, Any] | None = None
        fallback: dict[str, Any] | None = None
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            meta = data.get("_metadata", {}) if isinstance(data, dict) else {}
            origin = meta.get("story_id")
            if origin == story.id and same_story is None:
                same_story = data
            if fallback is None:
                fallback = data
        return same_story if same_story is not None else fallback
