import logging
import os
import sys
import json
from pathlib import Path
from typing import Any

from pipeline.agents import agent0_quality_gate, agent1_generate
from pipeline.context import ContextBuilder
from pipeline.log import setup
from pipeline.settings import get_settings
from pipeline.llm.factory import get_client

log = logging.getLogger("runner")


def run_phase3(
    client: Any,
    *,
    agent0_reports_dir: Path | None = None,
    test_cases_dir: Path | None = None,
) -> tuple[dict[str, Any], int]:
    builder = ContextBuilder.from_repo()
    agent0_destination = agent0_reports_dir or Path("generated") / "reports" / "agent0"
    test_cases_destination = test_cases_dir or Path("generated") / "test_cases"
    agent0_destination.mkdir(parents=True, exist_ok=True)
    test_cases_destination.mkdir(parents=True, exist_ok=True)

    agent0_results: list[dict[str, Any]] = []
    agent1_results: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    blobs = list(builder.build_all())
    if not blobs:
        log.warning("No story files found in data/user_stories/ — nothing to process.")
        aggregate = {
            "stage": "phase3_agent0_agent1",
            "total": 0,
            "agent0": [],
            "agent1": [],
            "blocked": [],
            "errors": [],
            "summary": {"agent0_ok": 0, "agent1_ok": 0, "blocked": 0, "errors": 0},
        }
        return aggregate, 1

    log.info("Found %d stories to process", len(blobs))

    for index, blob in enumerate(blobs, start=1):
        log.info("")
        log.info("=" * 60)
        log.info("  Story %d/%d — %s: %s", index, len(blobs), blob.story_id, blob.story.title)
        log.info("=" * 60)
        log.info("[%s] Running Agent 0 (quality gate)...", blob.story_id)
        try:
            agent0_output = agent0_quality_gate.run(blob, client)
            agent0_payload = agent0_output.to_dict()
            (agent0_destination / f"{blob.story_id}.json").write_text(
                json.dumps(agent0_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            agent0_results.append({"story_id": blob.story_id, "ok": True, "output": agent0_payload})

            if agent0_output.status == "APROVADA":
                log.info("[%s] Agent 0 → APROVADA", blob.story_id)
            else:
                n = len(agent0_output.problemas)
                log.warning(
                    "[%s] Agent 0 → PRECISA_DE_ESCLARECIMENTO (%d problem%s)",
                    blob.story_id,
                    n,
                    "s" if n != 1 else "",
                )

        except Exception as exc:
            log.error("[%s] Agent 0 → FAILED: %s: %s", blob.story_id, type(exc).__name__, exc)
            error = _error_payload(blob.story_id, "agent0", exc)
            agent0_results.append(error)
            errors.append(error)
            continue

        if agent0_output.status != "APROVADA":
            blocked.append({
                "story_id": blob.story_id,
                "reason": "agent0_needs_clarification",
                "agent0": agent0_payload,
            })
            continue

        log.info("[%s] Running Agent 1 (test case generation)...", blob.story_id)
        try:
            agent1_output = agent1_generate.run(blob, client)
            agent1_payload = agent1_output.to_dict()
            (test_cases_destination / f"{blob.story_id}.json").write_text(
                json.dumps(agent1_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            agent1_results.append({"story_id": blob.story_id, "ok": True, "output": agent1_payload})
            n_cases = len(agent1_output.test_cases)
            log.info(
                "[%s] Agent 1 → done — %d test case%s generated",
                blob.story_id,
                n_cases,
                "s" if n_cases != 1 else "",
            )
        except Exception as exc:
            log.error("[%s] Agent 1 → FAILED: %s: %s", blob.story_id, type(exc).__name__, exc)
            error = _error_payload(blob.story_id, "agent1", exc)
            agent1_results.append(error)
            errors.append(error)

    summary = {
        "agent0_ok": sum(1 for item in agent0_results if item.get("ok")),
        "agent1_ok": sum(1 for item in agent1_results if item.get("ok")),
        "blocked": len(blocked),
        "errors": len(errors),
    }
    log.info(
        "Done — total=%d | agent0_ok=%d | agent1_ok=%d | blocked=%d | errors=%d",
        len(agent0_results),
        summary["agent0_ok"],
        summary["agent1_ok"],
        summary["blocked"],
        summary["errors"],
    )

    aggregate = {
        "stage": "phase3_agent0_agent1",
        "total": len(agent0_results),
        "agent0": agent0_results,
        "agent1": agent1_results,
        "blocked": blocked,
        "errors": errors,
        "summary": summary,
    }
    return aggregate, 1 if blocked or errors else 0


def _error_payload(story_id: str, stage: str, exc: Exception) -> dict[str, Any]:
    return {
        "story_id": story_id,
        "stage": stage,
        "ok": False,
        "error": {
            "type": type(exc).__name__,
            "message": str(exc),
        },
    }


def main() -> None:
    settings = get_settings()
    setup(settings.log_level)

    provider = os.getenv("LLM_PROVIDER", "ollama")
    model = os.getenv(
        "LLM_MODEL",
        settings.ollama_pull_models[0] if settings.ollama_pull_models else "llama3",
    )
    provider_model = f"{provider}:{model}"
    log.info("Provider: %s", provider_model)

    try:
        client = get_client(provider_model, settings)
    except Exception as e:
        log.critical("Failed to instantiate LLM client: %s", e)
        sys.exit(1)

    aggregate, exit_code = run_phase3(client)
    aggregate["provider"] = provider
    aggregate["model"] = model
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
