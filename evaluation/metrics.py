import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFECT_INCORRECT_FACT = "IncorrectFact"


@dataclass(frozen=True)
class EvaluationPaths:
    generated_cases: Path
    scripts: Path
    agent2_reports: Path
    golden: Path
    results: Path


class EvaluationError(RuntimeError):
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Phase 7 evaluation metrics.")
    parser.add_argument("--generated-cases", default="generated/test_cases")
    parser.add_argument("--scripts", default="generated/scripts")
    parser.add_argument("--agent2-reports", default="generated/reports/agent2")
    parser.add_argument("--golden", default="data/golden")
    parser.add_argument("--results", default="evaluation/results")
    args = parser.parse_args()

    paths = EvaluationPaths(
        generated_cases=Path(args.generated_cases),
        scripts=Path(args.scripts),
        agent2_reports=Path(args.agent2_reports),
        golden=Path(args.golden),
        results=Path(args.results),
    )
    metrics = compute_metrics(paths)
    save_results(metrics, paths.results)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


def compute_metrics(paths: EvaluationPaths) -> dict[str, Any]:
    _require_dir(paths.generated_cases, "generated test cases")
    _require_dir(paths.scripts, "generated scripts")
    _require_dir(paths.agent2_reports, "Agent 2 reports")
    _require_dir(paths.golden, "golden oracle")

    generated = _load_generated_cases(paths.generated_cases)
    golden = _load_golden(paths.golden)
    reviews = _load_json(paths.golden / "generated_case_reviews.json")["reviews"]
    judge_reviews = _load_json(paths.golden / "judge_reviews.json")
    effort = _load_json(paths.golden / "effort_timings.json")

    _validate_generated_reviews(generated, reviews)
    _validate_golden_matches(generated, golden)

    case_quality = _case_quality_metrics(generated, golden, reviews)
    automation = _automation_metrics(paths.scripts, generated)
    judge = _judge_metrics(judge_reviews)
    effort_metrics = _effort_metrics(effort)

    return {
        "case_quality": case_quality,
        "automation_quality": automation,
        "judge_efficacy": judge,
        "perceived_effort": effort_metrics,
    }


def save_results(metrics: dict[str, Any], results_dir: Path) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (results_dir / "metrics.md").write_text(_to_markdown(metrics), encoding="utf-8")


def _load_generated_cases(path: Path) -> dict[str, list[dict[str, Any]]]:
    generated: dict[str, list[dict[str, Any]]] = {}
    for file in sorted(path.glob("US-*.json")):
        payload = _load_json(file)
        generated[file.stem] = payload["test_cases"]
    if not generated:
        raise EvaluationError(f"No generated test case files found in {path}.")
    return generated


def _load_golden(path: Path) -> dict[str, list[dict[str, Any]]]:
    golden: dict[str, list[dict[str, Any]]] = {}
    for file in sorted(path.glob("US-*.json")):
        payload = _load_json(file)
        story_id = payload["story_id"]
        golden[story_id] = payload["expected_cases"]
    if not golden:
        raise EvaluationError(f"No golden story files found in {path}.")
    return golden


def _case_quality_metrics(
    generated: dict[str, list[dict[str, Any]]],
    golden: dict[str, list[dict[str, Any]]],
    reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    review_by_case = {
        (review["story_id"], review["case_id"]): review
        for review in reviews
    }
    generated_total = sum(len(cases) for cases in generated.values())
    correct_total = sum(1 for review in reviews if review["correct"])
    expected_total = sum(len(cases) for cases in golden.values())
    matched_expected = sum(
        1
        for cases in golden.values()
        for case in cases
        if case["matched_generated_case_ids"]
    )
    precision = _safe_div(correct_total, generated_total)
    recall = _safe_div(matched_expected, expected_total)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    incorrect_fact_count = sum(
        1
        for review in reviews
        if DEFECT_INCORRECT_FACT in review.get("defect_tags", [])
    )
    return {
        "generated_cases": generated_total,
        "expected_cases": expected_total,
        "correct_generated_cases": correct_total,
        "matched_expected_cases": matched_expected,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "omission_rate": _safe_div(expected_total - matched_expected, expected_total),
        "incorrect_fact_rate": _safe_div(incorrect_fact_count, generated_total),
        "acceptance_criteria_coverage": _acceptance_criteria_coverage(generated, review_by_case),
    }


def _acceptance_criteria_coverage(
    generated: dict[str, list[dict[str, Any]]],
    review_by_case: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    criteria = _load_all_acceptance_criteria()
    covered: set[str] = set()
    for story_id, cases in generated.items():
        for case in cases:
            review = review_by_case[(story_id, case["id"])]
            if not review["correct"]:
                continue
            covered.update(case["criterios_cobertos"])
    return {
        "total": len(criteria),
        "covered": len(covered & criteria),
        "rate": _safe_div(len(covered & criteria), len(criteria)),
        "missing": sorted(criteria - covered),
    }


def _automation_metrics(scripts_dir: Path, generated: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    story_results = []
    for story_id in sorted(generated):
        story_dir = scripts_dir / story_id
        if not story_dir.is_dir():
            story_results.append({"story_id": story_id, "collect_ok": False, "error": "missing scripts dir"})
            continue
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", str(story_dir)],
            check=False,
            capture_output=True,
            text=True,
        )
        story_results.append(
            {
                "story_id": story_id,
                "collect_ok": result.returncode == 0,
                "error": "" if result.returncode == 0 else (result.stderr or result.stdout)[-1000:],
                "pendencias_de_automacao": _load_pending_count(story_dir),
            }
        )
    return {
        "script_collect_rate": _safe_div(
            sum(1 for result in story_results if result["collect_ok"]),
            len(story_results),
        ),
        "pending_automation_count": sum(result["pendencias_de_automacao"] for result in story_results),
        "stories": story_results,
        "functional_success_rate": None,
        "functional_success_rate_note": "Não calculado: Fase 6 foi pulada.",
    }


def _judge_metrics(judge_reviews: dict[str, Any]) -> dict[str, Any]:
    reported = judge_reviews["reported_problems"]
    missed = judge_reviews["missed_problems"]
    confirmed = sum(1 for item in reported if item["confirmed"])
    return {
        "reported_problems": len(reported),
        "confirmed_reported_problems": confirmed,
        "missed_human_problems": len(missed),
        "precision": _safe_div(confirmed, len(reported)),
        "recall": _safe_div(confirmed, confirmed + len(missed)),
    }


def _effort_metrics(effort: dict[str, Any]) -> dict[str, Any]:
    pipeline = float(effort["pipeline_review_minutes"])
    manual = float(effort["manual_authoring_minutes"])
    return {
        "pipeline_review_minutes": pipeline,
        "manual_authoring_minutes": manual,
        "manual_to_pipeline_ratio": _safe_div(manual, pipeline),
    }


def _validate_generated_reviews(
    generated: dict[str, list[dict[str, Any]]],
    reviews: list[dict[str, Any]],
) -> None:
    generated_ids = {
        (story_id, case["id"])
        for story_id, cases in generated.items()
        for case in cases
    }
    review_ids = {(review["story_id"], review["case_id"]) for review in reviews}
    missing = generated_ids - review_ids
    extra = review_ids - generated_ids
    if missing:
        raise EvaluationError(f"Missing generated case reviews: {sorted(missing)}.")
    if extra:
        raise EvaluationError(f"Review references unknown generated cases: {sorted(extra)}.")


def _validate_golden_matches(
    generated: dict[str, list[dict[str, Any]]],
    golden: dict[str, list[dict[str, Any]]],
) -> None:
    generated_ids = {
        (story_id, case["id"])
        for story_id, cases in generated.items()
        for case in cases
    }
    for story_id, cases in golden.items():
        for case in cases:
            for generated_id in case["matched_generated_case_ids"]:
                if (story_id, generated_id) not in generated_ids:
                    raise EvaluationError(
                        f"Golden case {case['id']} references unknown generated case {generated_id}."
                    )


def _load_all_acceptance_criteria() -> set[str]:
    criteria: set[str] = set()
    for file in (REPO_ROOT / "data" / "user_stories").glob("US-*.yaml"):
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
        criteria.update(str(item["id"]) for item in data["acceptance_criteria"])
    return criteria


def _load_pending_count(story_dir: Path) -> int:
    path = story_dir / "pendencias_de_automacao.json"
    if not path.is_file():
        return 0
    return len(json.loads(path.read_text(encoding="utf-8")))


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise EvaluationError(f"Required file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _require_dir(path: Path, label: str) -> None:
    if not path.is_dir():
        raise EvaluationError(f"Required {label} directory not found: {path}")


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _to_markdown(metrics: dict[str, Any]) -> str:
    quality = metrics["case_quality"]
    automation = metrics["automation_quality"]
    judge = metrics["judge_efficacy"]
    effort = metrics["perceived_effort"]
    return (
        "# Phase 7 Metrics\n\n"
        "| Metric | Value |\n"
        "|---|---:|\n"
        f"| Precision | {quality['precision']} |\n"
        f"| Recall | {quality['recall']} |\n"
        f"| F1 | {quality['f1']} |\n"
        f"| Omission rate | {quality['omission_rate']} |\n"
        f"| Incorrect-fact rate | {quality['incorrect_fact_rate']} |\n"
        f"| AC coverage | {quality['acceptance_criteria_coverage']['rate']} |\n"
        f"| Script collect rate | {automation['script_collect_rate']} |\n"
        f"| Judge precision | {judge['precision']} |\n"
        f"| Judge recall | {judge['recall']} |\n"
        f"| Manual/pipeline effort ratio | {effort['manual_to_pipeline_ratio']} |\n"
    )


if __name__ == "__main__":
    main()
