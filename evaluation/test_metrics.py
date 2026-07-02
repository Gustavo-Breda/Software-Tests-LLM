import json
from pathlib import Path

from evaluation.metrics import EvaluationPaths, compute_metrics


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_compute_metrics_with_complete_fixture(tmp_path):
    generated = tmp_path / "generated" / "test_cases"
    scripts = tmp_path / "generated" / "scripts"
    agent2 = tmp_path / "generated" / "reports" / "agent2"
    golden = tmp_path / "data" / "golden"
    results = tmp_path / "evaluation" / "results"
    agent2.mkdir(parents=True)

    _write_json(
        generated / "US-01.json",
        {
            "test_cases": [
                {
                    "id": "TC-01-01",
                    "criterios_cobertos": ["CA-01.1"],
                    "tipo": "positivo",
                },
                {
                    "id": "TC-01-02",
                    "criterios_cobertos": ["CA-01.2"],
                    "tipo": "negativo",
                },
            ]
        },
    )
    _write_json(
        golden / "US-01.json",
        {
            "story_id": "US-01",
            "expected_cases": [
                {
                    "id": "EXP-01-01",
                    "titulo": "Login ok",
                    "criterios_cobertos": ["CA-01.1"],
                    "tipo": "positivo",
                    "must_cover": "Login válido.",
                    "matched_generated_case_ids": ["TC-01-01"],
                },
                {
                    "id": "EXP-01-02",
                    "titulo": "Login inválido",
                    "criterios_cobertos": ["CA-01.2"],
                    "tipo": "negativo",
                    "must_cover": "Erro genérico.",
                    "matched_generated_case_ids": [],
                },
            ],
        },
    )
    _write_json(
        golden / "generated_case_reviews.json",
        {
            "reviews": [
                {
                    "story_id": "US-01",
                    "case_id": "TC-01-01",
                    "correct": True,
                    "defect_tags": [],
                },
                {
                    "story_id": "US-01",
                    "case_id": "TC-01-02",
                    "correct": False,
                    "defect_tags": ["IncorrectFact"],
                },
            ]
        },
    )
    _write_json(
        golden / "judge_reviews.json",
        {
            "reported_problems": [
                {"story_id": "US-01", "case_id": "TC-01-02", "confirmed": True}
            ],
            "missed_problems": [
                {"story_id": "US-01", "case_id": "TC-01-03", "tipo": "Omission"}
            ],
        },
    )
    _write_json(
        golden / "effort_timings.json",
        {
            "pipeline_review_minutes": 10,
            "manual_authoring_minutes": 30,
        },
    )
    story_scripts = scripts / "US-01"
    story_scripts.mkdir(parents=True)
    (story_scripts / "test_us_01.py").write_text("def test_collects():\n    assert True\n", encoding="utf-8")
    _write_json(story_scripts / "pendencias_de_automacao.json", [])

    metrics = compute_metrics(
        EvaluationPaths(
            generated_cases=generated,
            scripts=scripts,
            agent2_reports=agent2,
            golden=golden,
            results=results,
        )
    )

    assert metrics["case_quality"]["precision"] == 0.5
    assert metrics["case_quality"]["recall"] == 0.5
    assert metrics["case_quality"]["f1"] == 0.5
    assert metrics["case_quality"]["omission_rate"] == 0.5
    assert metrics["case_quality"]["incorrect_fact_rate"] == 0.5
    assert metrics["automation_quality"]["script_collect_rate"] == 1.0
    assert metrics["judge_efficacy"]["precision"] == 1.0
    assert metrics["judge_efficacy"]["recall"] == 0.5
    assert metrics["perceived_effort"]["manual_to_pipeline_ratio"] == 3.0
