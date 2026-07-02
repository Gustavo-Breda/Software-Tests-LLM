# Golden oracle contract

Phase 7 requires human-reviewed oracle files before metrics can run.

Required files:

- `US-XX.json`: expected scenario-level cases for each story.
- `generated_case_reviews.json`: one human review per generated case.
- `judge_reviews.json`: human confirmation of Agent 2 findings and missed findings.
- `effort_timings.json`: manual effort timings.

`US-XX.json` shape:

```json
{
  "story_id": "US-01",
  "expected_cases": [
    {
      "id": "EXP-01-01",
      "titulo": "Login bem-sucedido",
      "criterios_cobertos": ["CA-01.1"],
      "tipo": "positivo",
      "must_cover": "Credenciais válidas retornam 200 e redirecionam para /requests.",
      "matched_generated_case_ids": ["TC-01-01"]
    }
  ]
}
```

Do not derive expected cases from `generated/test_cases`. Build them from
`data/user_stories`, app behavior, and human review.
