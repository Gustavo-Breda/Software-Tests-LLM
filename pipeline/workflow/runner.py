import os
import sys
import json
from pathlib import Path
from typing import Any

from pipeline.agents import agent0_quality_gate, agent1_generate, agent2_judge
from pipeline.context import ContextBuilder
from pipeline.settings import get_settings
from pipeline.llm.factory import get_client


def run_agent0_all(
    client: Any,
    *,
    reports_dir: Path | None = None,
) -> tuple[dict[str, Any], int]:
    print("[runner] run_agent0_all start")
    builder = ContextBuilder.from_repo()
    destination = reports_dir or Path("generated") / "reports" / "agent0"
    destination.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    has_error = False

    for blob in builder.build_all():
        print(f"[runner] agent0 story={blob.story_id}")
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
            print(f"[runner] agent0 saved story={blob.story_id} path={report_path}")
        except Exception as exc:
            has_error = True
            print(f"[runner] agent0 error story={blob.story_id} type={type(exc).__name__}: {exc}")
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


def run_phase4(
    client: Any,
    *,
    agent0_reports_dir: Path | None = None,
    test_cases_dir: Path | None = None,
    agent2_reports_dir: Path | None = None,
    repaired_test_cases_dir: Path | None = None,
) -> tuple[dict[str, Any], int]:
    builder = ContextBuilder.from_repo()
    agent0_destination = agent0_reports_dir or Path("generated") / "reports" / "agent0"
    test_cases_destination = test_cases_dir or Path("generated") / "test_cases"
    agent2_destination = agent2_reports_dir or Path("generated") / "reports" / "agent2"
    repaired_destination = repaired_test_cases_dir or Path("generated") / "test_cases_repaired"
    agent0_destination.mkdir(parents=True, exist_ok=True)
    test_cases_destination.mkdir(parents=True, exist_ok=True)
    agent2_destination.mkdir(parents=True, exist_ok=True)
    repaired_destination.mkdir(parents=True, exist_ok=True)
    print(
        "[runner] phase4 start "
        f"agent0_dir={agent0_destination} test_cases_dir={test_cases_destination} "
        f"agent2_dir={agent2_destination} repaired_dir={repaired_destination}"
    )

    agent0_results: list[dict[str, Any]] = []
    agent1_results: list[dict[str, Any]] = []
    agent2_results: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    repair_attempts: list[dict[str, Any]] = []
    rejected_after_repair = 0

    for blob in builder.build_all():
        print(f"[runner] story start story={blob.story_id}")
        try:
            agent0_output = agent0_quality_gate.run(blob, client)
            agent0_payload = agent0_output.to_dict()
            (agent0_destination / f"{blob.story_id}.json").write_text(
                json.dumps(agent0_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"[runner] agent0 saved story={blob.story_id}")
            agent0_results.append(
                {
                    "story_id": blob.story_id,
                    "ok": True,
                    "output": agent0_payload,
                }
            )
        except Exception as exc:
            error = _error_payload(blob.story_id, "agent0", exc)
            print(f"[runner] agent0 error story={blob.story_id} type={type(exc).__name__}: {exc}")
            agent0_results.append(error)
            errors.append(error)
            continue

        if agent0_output.status != "APROVADA":
            print(f"[runner] story blocked story={blob.story_id} status={agent0_output.status}")
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
            print(f"[runner] agent1 saved story={blob.story_id}")
            agent1_results.append(
                {
                    "story_id": blob.story_id,
                    "ok": True,
                    "output": agent1_payload,
                }
            )
        except Exception as exc:
            error = _error_payload(blob.story_id, "agent1", exc)
            print(f"[runner] agent1 error story={blob.story_id} type={type(exc).__name__}: {exc}")
            agent1_results.append(error)
            errors.append(error)
            continue

        try:
            judge_result = agent2_judge.run(blob, agent1_output, client)
            for attempt_index, attempt_report in enumerate(judge_result.attempt_reports):
                report_path = agent2_destination / f"{blob.story_id}_attempt-{attempt_index}.json"
                report_path.write_text(
                    json.dumps(attempt_report.to_dict(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                print(f"[runner] agent2 saved story={blob.story_id} attempt={attempt_index} path={report_path}")
            for repair_output in judge_result.repair_generations:
                repair_path = repaired_destination / f"{blob.story_id}_attempt-{repair_output.attempt}.json"
                repair_path.write_text(
                    json.dumps(repair_output.output.to_dict(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                print(f"[runner] repair saved story={blob.story_id} attempt={repair_output.attempt} path={repair_path}")
            if judge_result.repair_generations:
                final_path = repaired_destination / f"{blob.story_id}_final.json"
                final_path.write_text(
                    json.dumps(judge_result.final_generation.to_dict(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                print(f"[runner] repair final saved story={blob.story_id} path={final_path}")
            agent2_results.append(
                {
                    "story_id": blob.story_id,
                    "ok": True,
                    "output": judge_result.final_output.to_dict(),
                    "repair_attempts": judge_result.repair_attempts,
                    "rejected_after_repair": judge_result.rejected_after_repair,
                }
            )
            repair_attempts.append(
                {
                    "story_id": blob.story_id,
                    "count": judge_result.repair_attempts,
                }
            )
            if judge_result.rejected_after_repair:
                print(f"[runner] story rejected_after_repair story={blob.story_id}")
                rejected_after_repair += 1
            else:
                print(
                    f"[runner] story done story={blob.story_id} "
                    f"repair_attempts={judge_result.repair_attempts} "
                    f"decision={judge_result.final_output.decisao}"
                )
        except Exception as exc:
            error = _error_payload(blob.story_id, "agent2", exc)
            print(f"[runner] agent2 error story={blob.story_id} type={type(exc).__name__}: {exc}")
            agent2_results.append(error)
            errors.append(error)

    aggregate = {
        "stage": "phase4_agent0_agent1_agent2",
        "total": len(agent0_results),
        "agent0": agent0_results,
        "agent1": agent1_results,
        "agent2": agent2_results,
        "repair_attempts": repair_attempts,
        "blocked": blocked,
        "errors": errors,
        "summary": {
            "agent0_ok": sum(1 for item in agent0_results if item.get("ok")),
            "agent1_ok": sum(1 for item in agent1_results if item.get("ok")),
            "agent2_ok": sum(1 for item in agent2_results if item.get("ok")),
            "repair_attempts": sum(item["count"] for item in repair_attempts),
            "blocked": len(blocked),
            "errors": len(errors),
            "rejected_after_repair": rejected_after_repair,
        },
    }
    print(
        "[runner] phase4 done "
        f"agent0_ok={aggregate['summary']['agent0_ok']} "
        f"agent1_ok={aggregate['summary']['agent1_ok']} "
        f"agent2_ok={aggregate['summary']['agent2_ok']} "
        f"blocked={aggregate['summary']['blocked']} "
        f"errors={aggregate['summary']['errors']} "
        f"repair_attempts={aggregate['summary']['repair_attempts']} "
        f"rejected_after_repair={aggregate['summary']['rejected_after_repair']}"
    )
    return aggregate, 1 if blocked or errors or rejected_after_repair else 0


def run_phase3(
    client: Any,
    *,
    agent0_reports_dir: Path | None = None,
    test_cases_dir: Path | None = None,
) -> tuple[dict[str, Any], int]:
    return run_phase4(
        client,
        agent0_reports_dir=agent0_reports_dir,
        test_cases_dir=test_cases_dir,
    )


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

    print(f"[runner] client ready provider={provider} model={model}")
    aggregate, exit_code = run_phase4(client)
    aggregate["provider"] = provider
    aggregate["model"] = model
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
