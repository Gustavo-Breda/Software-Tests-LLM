from dataclasses import dataclass

from .builder import REQUIRED_SECTIONS
from .models import ContextBlob


@dataclass
class VerificationResult:
    story_id: str
    ok: bool
    char_count: int
    token_estimate: int
    section_titles: list[str]
    missing_sections: list[str]
    notes: list[str]


def verify_complete(blob: ContextBlob) -> VerificationResult:
    titles = blob.section_titles()
    missing = [t for t in REQUIRED_SECTIONS if t not in titles]

    notes: list[str] = []
    text = blob.text

    # Every acceptance criterion ID must appear in the rendered text.
    for crit in blob.story.acceptance_criteria:
        cid = crit.get("id")
        if cid and cid not in text:
            notes.append(f"Critério {cid} não aparece no blob renderizado.")

    # The story ID must appear.
    if blob.story.id not in text:
        notes.append(f"ID da story ({blob.story.id}) ausente no blob.")

    # At least one selector should be present (every story touches some UI).
    if "data-testid" not in text:
        notes.append("Nenhum seletor `data-testid` no blob — verificar ui_map.")

    return VerificationResult(
        story_id=blob.story_id,
        ok=not missing and not notes,
        char_count=blob.char_count,
        token_estimate=blob.token_estimate,
        section_titles=titles,
        missing_sections=missing,
        notes=notes,
    )
