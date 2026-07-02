import logging
import os
import sys
import json
import re
from pathlib import Path
from typing import Any

from pipeline.agents import agent0_quality_gate, agent1_generate, agent2_judge, agent3_codegen
from pipeline.agents.agent1_generate import GenerationOutput, TestCase
from pipeline.context import ContextBuilder
from pipeline.log import setup
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
log = logging.getLogger("runner")


def run_phase5(
    client: Any,
    *,
    agent0_reports_dir: Path | None = None,
    test_cases_dir: Path | None = None,
    agent2_reports_dir: Path | None = None,
    repaired_test_cases_dir: Path | None = None,
    scripts_dir: Path | None = None,
) -> tuple[dict[str, Any], int]:
    agent2_destination = agent2_reports_dir or Path("generated") / "reports" / "agent2"
    test_cases_destination = test_cases_dir or Path("generated") / "test_cases"
    repaired_destination = repaired_test_cases_dir or Path("generated") / "test_cases_repaired"
    scripts_destination = scripts_dir or Path("generated") / "scripts"

    phase4_aggregate, phase4_exit = run_phase4(
        client,
        agent0_reports_dir=agent0_reports_dir,
        test_cases_dir=test_cases_destination,
        agent2_reports_dir=agent2_destination,
        repaired_test_cases_dir=repaired_destination,
    )

    builder = ContextBuilder.from_repo()
    scripts_destination.mkdir(parents=True, exist_ok=True)
    codegen_results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for blob in builder.build_all():
        final_judge = _load_final_judge_report(agent2_destination, blob.story_id)
        if not final_judge or final_judge.get("decisao") != "APROVADO":
            codegen_results.append(
                {
                    "story_id": blob.story_id,
                    "ok": False,
                    "skipped": True,
                    "reason": "agent2_not_approved",
                }
            )
            continue

        try:
            generation = _load_final_generation(
                blob.story_id,
                test_cases_destination,
                repaired_destination,
            )
            output = agent3_codegen.run(blob, generation, client)
            story_scripts_dir = scripts_destination / blob.story_id
            agent3_codegen.save_to_disk(output, story_scripts_dir)
            codegen_results.append(
                {
                    "story_id": blob.story_id,
                    "ok": True,
                    "files": sorted(output.arquivos),
                    "pendencias_de_automacao": output.pendencias_de_automacao,
                    "path": str(story_scripts_dir),
                }
            )
            print(f"[runner] agent3 saved story={blob.story_id} path={story_scripts_dir}")
        except Exception as exc:
            error = _error_payload(blob.story_id, "agent3", exc)
            codegen_results.append(error)
            errors.append(error)
            print(f"[runner] agent3 error story={blob.story_id} type={type(exc).__name__}: {exc}")

    aggregate = {
        "stage": "phase5_agent3_codegen",
        "phase4": phase4_aggregate,
        "agent3": codegen_results,
        "summary": {
            "agent3_ok": sum(1 for item in codegen_results if item.get("ok")),
            "agent3_skipped": sum(1 for item in codegen_results if item.get("skipped")),
            "agent3_errors": len(errors),
        },
    }
    exit_code = 1 if phase4_exit or errors else 0
    print(
        "[runner] phase5 done "
        f"agent3_ok={aggregate['summary']['agent3_ok']} "
        f"skipped={aggregate['summary']['agent3_skipped']} "
        f"errors={aggregate['summary']['agent3_errors']}"
    )
    return aggregate, exit_code


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
            print(f"[runner] agent0 error story={blob.story_id} type={type(exc).__name__}: {exc}")
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
            print(f"[runner] agent1 error story={blob.story_id} type={type(exc).__name__}: {exc}")
            agent1_results.append(error)
            errors.append(error)
            continue

        log.info("[%s] Running Agent 2 (judge + repair loop)...", blob.story_id)
        try:
            judge_result = agent2_judge.run(blob, agent1_output, client)
            for attempt_index, attempt_report in enumerate(judge_result.attempt_reports):
                report_path = agent2_destination / f"{blob.story_id}_attempt-{attempt_index}.json"
                report_path.write_text(
                    json.dumps(attempt_report.to_dict(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                log.info(
                    "[%s] Agent 2 attempt-%d saved — decision=%s approved=%d rejected=%d problems=%d omitted=%d path=%s",
                    blob.story_id,
                    attempt_index,
                    attempt_report.decisao,
                    len(attempt_report.casos_aprovados),
                    len(attempt_report.casos_reprovados),
                    len(attempt_report.problemas),
                    len(attempt_report.cenarios_omitidos_sugeridos),
                    report_path,
                )
                print(f"[runner] agent2 saved story={blob.story_id} attempt={attempt_index} path={report_path}")
            for repair_output in judge_result.repair_generations:
                repair_path = repaired_destination / f"{blob.story_id}_attempt-{repair_output.attempt}.json"
                repair_path.write_text(
                    json.dumps(repair_output.output.to_dict(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                log.info(
                    "[%s] Repair attempt-%d saved — cases=%d alerts=%d path=%s",
                    blob.story_id,
                    repair_output.attempt,
                    len(repair_output.output.test_cases),
                    len(repair_output.output.alertas),
                    repair_path,
                )
                print(f"[runner] repair saved story={blob.story_id} attempt={repair_output.attempt} path={repair_path}")
            if judge_result.repair_generations:
                final_path = repaired_destination / f"{blob.story_id}_final.json"
                final_path.write_text(
                    json.dumps(judge_result.final_generation.to_dict(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                log.info(
                    "[%s] Repair final saved — cases=%d alerts=%d path=%s",
                    blob.story_id,
                    len(judge_result.final_generation.test_cases),
                    len(judge_result.final_generation.alertas),
                    final_path,
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
                log.error(
                    "[%s] Agent 2 → REPROVADO after %d repair attempt(s)",
                    blob.story_id,
                    judge_result.repair_attempts,
                )
                print(f"[runner] story rejected_after_repair story={blob.story_id}")
                rejected_after_repair += 1
            else:
                log.info(
                    "[%s] Agent 2 → %s after %d repair attempt(s)",
                    blob.story_id,
                    judge_result.final_output.decisao,
                    judge_result.repair_attempts,
                )
                print(
                    f"[runner] story done story={blob.story_id} "
                    f"repair_attempts={judge_result.repair_attempts} "
                    f"decision={judge_result.final_output.decisao}"
                )
        except Exception as exc:
            log.error("[%s] Agent 2 → FAILED: %s: %s", blob.story_id, type(exc).__name__, exc)
            error = _error_payload(blob.story_id, "agent2", exc)
            print(f"[runner] agent2 error story={blob.story_id} type={type(exc).__name__}: {exc}")
            agent2_results.append(error)
            errors.append(error)

    summary = {
        "agent0_ok": sum(1 for item in agent0_results if item.get("ok")),
        "agent1_ok": sum(1 for item in agent1_results if item.get("ok")),
        "blocked": len(blocked),
        "errors": len(errors),
    }
    log.info(
        "Done — total=%d | agent0_ok=%d | agent1_ok=%d | agent2_ok=%d | blocked=%d | errors=%d | repair_attempts=%d | rejected_after_repair=%d",
        len(agent0_results),
        sum(1 for item in agent0_results if item.get("ok")),
        sum(1 for item in agent1_results if item.get("ok")),
        sum(1 for item in agent2_results if item.get("ok")),
        len(blocked),
        len(errors),
        sum(item["count"] for item in repair_attempts),
        rejected_after_repair,
    )

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


def _load_final_judge_report(agent2_dir: Path, story_id: str) -> dict[str, Any] | None:
    reports = sorted(
        agent2_dir.glob(f"{story_id}_attempt-*.json"),
        key=lambda path: _attempt_number(path),
    )
    if not reports:
        return None
    return json.loads(reports[-1].read_text(encoding="utf-8"))


def _attempt_number(path: Path) -> int:
    match = re.search(r"_attempt-(\d+)\.json$", path.name)
    return int(match.group(1)) if match else -1


def _load_final_generation(
    story_id: str,
    test_cases_dir: Path,
    repaired_test_cases_dir: Path,
) -> GenerationOutput:
    repaired_path = repaired_test_cases_dir / f"{story_id}_final.json"
    source = repaired_path if repaired_path.is_file() else test_cases_dir / f"{story_id}.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    return GenerationOutput(
        test_cases=[TestCase(**case) for case in data["test_cases"]],
        matriz_rastreabilidade=data["matriz_rastreabilidade"],
        alertas=data["alertas"],
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

    print(f"[runner] client ready provider={provider} model={model}")
    phase = os.getenv("PIPELINE_PHASE", "phase4").strip().lower()
    if phase == "phase5":
        aggregate, exit_code = run_phase5(client)
    elif phase == "phase4":
        aggregate, exit_code = run_phase4(client)
    else:
        log.critical("Unsupported PIPELINE_PHASE: %s", phase)
        sys.exit(1)
    aggregate["provider"] = provider
    aggregate["model"] = model
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
