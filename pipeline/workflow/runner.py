import os
import sys
import json
from pathlib import Path
from typing import Any

from pipeline.agents import agent0_quality_gate, agent1_generate
from pipeline.context import ContextBuilder
from pipeline.settings import get_settings
from pipeline.llm.factory import get_client


def run_agent0_all(
    client: Any,
    *,
    reports_dir: Path | None = None,
) -> tuple[dict[str, Any], int]:
    builder = ContextBuilder.from_repo()
    destination = reports_dir or Path("generated") / "reports" / "agent0"
    destination.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    has_error = False

    for blob in builder.build_all():
        try:
            output = agent0_quality_gate.run(blob, client)
            result = {
                "story_id": blob.story_id,
                "ok": True,
                "output": output.to_dict(),
            }
            report_path = destination / f"{blob.story_id}.json"
            report_path.write_text(
                json.dumps(output.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            has_error = True
            result = {
                "story_id": blob.story_id,
                "ok": False,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }
        results.append(result)

    aggregate = {
        "stage": "agent0_quality_gate",
        "total": len(results),
        "failed": sum(1 for item in results if not item["ok"]),
        "results": results,
    }
    return aggregate, 1 if has_error else 0


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

    for blob in builder.build_all():
        try:
            agent0_output = agent0_quality_gate.run(blob, client)
            agent0_payload = agent0_output.to_dict()
            (agent0_destination / f"{blob.story_id}.json").write_text(
                json.dumps(agent0_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            agent0_results.append(
                {
                    "story_id": blob.story_id,
                    "ok": True,
                    "output": agent0_payload,
                }
            )
        except Exception as exc:
            error = _error_payload(blob.story_id, "agent0", exc)
            agent0_results.append(error)
            errors.append(error)
            continue

        if agent0_output.status != "APROVADA":
            blocked.append(
                {
                    "story_id": blob.story_id,
                    "reason": "agent0_needs_clarification",
                    "agent0": agent0_payload,
                }
            )
            continue

        try:
            agent1_output = agent1_generate.run(blob, client)
            agent1_payload = agent1_output.to_dict()
            (test_cases_destination / f"{blob.story_id}.json").write_text(
                json.dumps(agent1_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            agent1_results.append(
                {
                    "story_id": blob.story_id,
                    "ok": True,
                    "output": agent1_payload,
                }
            )
        except Exception as exc:
            error = _error_payload(blob.story_id, "agent1", exc)
            agent1_results.append(error)
            errors.append(error)

    aggregate = {
        "stage": "phase3_agent0_agent1",
        "total": len(agent0_results),
        "agent0": agent0_results,
        "agent1": agent1_results,
        "blocked": blocked,
        "errors": errors,
        "summary": {
            "agent0_ok": sum(1 for item in agent0_results if item.get("ok")),
            "agent1_ok": sum(1 for item in agent1_results if item.get("ok")),
            "blocked": len(blocked),
            "errors": len(errors),
        },
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

    provider = os.getenv("LLM_PROVIDER", "ollama")
    model = os.getenv(
        "LLM_MODEL",
        settings.ollama_pull_models[0] if settings.ollama_pull_models else "llama3",
    )

    provider_model = f"{provider}:{model}"

    try:
        client = get_client(provider_model, settings)
    except Exception as e:
        print(f"Error instantiating client: {e}")
        sys.exit(1)

    aggregate, exit_code = run_phase3(client)
    aggregate["provider"] = provider
    aggregate["model"] = model
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
