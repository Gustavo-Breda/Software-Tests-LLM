# Code Review — Consolidated Findings
**Date:** 2026-07-01
**Reviewer:** Senior (independent pass) + Junior (initial pass)
**Scope:** Full codebase + comparison against `docs/article.txt`

---

## How to read this document

Each finding has a status badge:
- **FIXED** — already corrected in the working tree before this review ran.
- **OPEN** — still present; action required.

Findings are ordered by severity within each group.

---

## Fixed findings (already applied)

### [CRITICAL] FINDING-1: `_validate_strict_gate` logic bug — only caught simultaneous violations
- Status: **FIXED**
- File: `pipeline/agents/agent0_quality_gate.py:103`
- Description: The `PRECISA_DE_ESCLARECIMENTO` invariant (`derivavel=false` AND `problemas≠[]`) was enforced with `and derivavel and not problemas` — this only raised if BOTH conditions were violated simultaneously. A payload with `derivavel=True` but non-empty `problemas`, or `derivavel=False` with empty `problemas`, silently passed.
- Failure scenario: Agent LLM returns `{"status": "PRECISA_DE_ESCLARECIMENTO", "derivavel": true, "problemas": [...]}` — pipeline would accept the contradictory output and continue.
- Fix: Changed to `and (derivavel or not problemas)`. Two regression tests added.

### [HIGH] FINDING-2: `ContextBlob.text` caused double/triple injection of sections into agent prompts
- Status: **FIXED**
- Files: `pipeline/context/models.py`, `pipeline/agents/agent0_quality_gate.py`, `pipeline/agents/agent1_generate.py`
- Description: `blob.text` concatenates ALL 6 context sections, including the story itself, the glossary, and the few-shot examples. Both agent prompts used `blob.text` as `{system_context}`, so: Agent 0 received the story twice; Agent 1 received the story, glossary, and few-shot examples twice each. This wastes tokens and may cause the LLM to weight repeated sections disproportionately.
- Fix: Added `ContextBlob.filtered_text(exclude: set[str])`. Agent 0 excludes the story section; Agent 1 excludes the story, glossary, and examples sections from `{system_context}`.

### [HIGH] FINDING-3: Backend Docker image excluded pytest/httpx (`--only main`)
- Status: **FIXED**
- File: `docker/Dockerfile.backend`
- Description: `poetry install --only main` excluded the `dev` group, which contains `pytest` and `httpx`. Running `docker compose run --rm backend pytest` found no tests and exited silently.
- Fix: Removed `--only main`.

### [MEDIUM] FINDING-4: `pytest.ini` at root had no `testpaths` — collected backend tests by accident
- Status: **FIXED**
- File: `pytest.ini`
- Description: Without `testpaths`, `pytest` collected `app/backend/tests/` and failed on import (`src.main` not in root pythonpath).
- Fix: Added `testpaths = pipeline/tests`.

---

## Open findings

### [HIGH] FINDING-5: Article repair prompt uses `CT-format` IDs — will fail Agent 1 schema validation in Phase 4
- Status: **OPEN**
- Files: `docs/article.txt:480-483`, `pipeline/schemas/agent1_out.json:32`, `pipeline/prompts/04_repair.txt`
- Description: The article's repair prompt (§8.4, page 16) explicitly instructs the LLM: *"Mantenha o ID original se for correção; use novo ID (CT-0XX) se for substituição completa."* The Agent 1 output schema enforces `^TC-[0-9]{2}-[0-9]{2}$`. Any new test case generated during repair with a `CT-`-prefix ID will immediately fail `validate_schema(data, "agent1_out.json")` and raise `AgentOutputError`, crashing the entire repair loop.
- Failure scenario: Phase 4 implements repair by passing the article's prompt verbatim → Agent LLM generates `{"id": "CT-004", ...}` for a new scenario → `AgentOutputError: Schema validation failed at test_cases.4.id: 'CT-004' does not match '^TC-[0-9]{2}-[0-9]{2}$'`.
- Recommendation: Rewrite the repair prompt's ID instruction to use TC-format before Phase 4 implementation. Document this deviation from the article in `docs/PLAN.md §decision-log`.

### [HIGH] FINDING-6: Article traceability matrix uses `casos_de_teste` field; schema uses `casos` — repair output will fail validation
- Status: **OPEN**
- Files: `docs/article.txt:364`, `pipeline/schemas/agent1_out.json:98`
- Description: The article's `matriz_rastreabilidade` format (§8.2 and §8.4) uses the field name `casos_de_teste`. The implementation schema requires `casos`. When Phase 4 prompts follow the article verbatim, the LLM will output `casos_de_teste`, which is not in the schema's `required` array and not in `properties`, causing `additionalProperties: false` validation failure.
- Failure scenario: Repair agent outputs `{"criterio": "CA-01.1", "casos_de_teste": ["TC-01-01"]}` → schema validation fails with `"Additional properties are not allowed ('casos_de_teste' was unexpected)"`.
- Recommendation: Align Phase 4 prompts with the `casos` field name. Document in `docs/PLAN.md §decision-log`.

### [HIGH] FINDING-7: `tipo` enum truncated from 5 to 3 values — Phase 4 repair will generate schema-invalid output
- Status: **OPEN**
- File: `pipeline/schemas/agent1_out.json:52`, `docs/article.txt:346`
- Description: The article specifies `tipo` as `"positivo | negativo | borda | permissao | regressao"` (5 values). The schema only allows `["positivo", "negativo", "borda"]`. The article's repair prompt (§8.4) instructs the LLM to preserve original test case structure, which may include `permissao` or `regressao` types from the judge's `cenarios_omitidos_sugeridos`. Any such case will fail schema validation.
- Failure scenario: Judge suggests a `permissao`-type test case in `cenarios_omitidos_sugeridos` → repair agent generates it → schema rejects it → entire repaired batch rejected.
- Recommendation: Either add `permissao` and `regressao` to the schema enum, or explicitly prohibit these types in the repair prompt and document the decision.

### [HIGH] FINDING-8: Phase 6 network architecture conflict — `network_mode: host` blocks Docker service hostnames
- Status: **OPEN**
- File: `docker-compose.yml:80`
- Description: The `pipeline` service uses `network_mode: host` to reach Ollama at `localhost:11434`. With `network_mode: host`, the container is NOT part of `llm-tests-network`, so Docker bridge service hostnames (`selenium:4444`, `backend:8000`, `frontend:5173`) are unreachable. Phase 6 Selenium tests must be run FROM the pipeline container pointing at the Selenium Grid container.
- Failure scenario: Phase 6 test script targets `http://selenium:4444` → DNS lookup fails → all tests abort with connection error.
- Recommendation: For Phase 6, either (a) remove `network_mode: host` and route Ollama traffic through the published port (`host.docker.internal:11434` on Mac/Win, or explicit host IP on Linux), or (b) launch a separate `test-runner` service that is in the bridge network and doesn't need Ollama. Document the chosen approach in `docs/PLAN.md`.

### [MEDIUM] FINDING-9: Missing backend test for CA-01.4 (invalid email format → 422 on login)
- Status: **OPEN**
- File: `app/backend/tests/test_auth.py`
- Description: `data/user_stories/US-01.yaml` includes CA-01.4: *"Tentar realizar login com um e-mail em formato inválido retorna 422 Unprocessable Entity."* The backend implements this correctly (Pydantic `EmailStr` on `LoginIn` rejects malformed input with 422), but there is no test covering this criterion. The three other CA-01 criteria each have corresponding tests.
- Failure scenario: If someone replaces `EmailStr` with `str` in `LoginIn` (looser validation), all existing tests still pass. The missing test fails to catch the regression.
- Recommendation: Add `test_login_invalid_email_format_returns_422` to `test_auth.py`.

### [MEDIUM] FINDING-10: Traceability matrix `casos` allows empty array — `_validate_semantics` does not catch it
- Status: **OPEN**
- File: `pipeline/schemas/agent1_out.json:103-110`, `pipeline/agents/agent1_generate.py:150-155`
- Description: The matrix entry schema (`"casos": {"type": "array", "items": {...}}`) has no `minItems: 1`. A matrix entry like `{"criterio": "CA-01.2", "casos": []}` passes schema validation. The semantic validator checks bidirectional consistency between test cases and the matrix, but if `casos` is empty there are no cases to cross-check — the check trivially passes. A criterion can appear in the matrix with zero covering tests, silently satisfying the "all criteria have a matrix entry" invariant.
- Failure scenario: LLM outputs `{"criterio": "CA-01.3", "casos": []}` — pipeline accepts it. The test suite reports 0 test cases for the lockout criterion, but `summary.agent1_ok == True`. Evaluation metrics will undercount test coverage silently.
- Recommendation: Add `"minItems": 1` to the `casos` array in `agent1_out.json`, and add a semantic validation check in `_validate_semantics`.

### [MEDIUM] FINDING-11: `03_judge.txt` placeholder stub specifies 0.0–1.0 score range; article specifies 0–10 integers
- Status: **OPEN**
- File: `pipeline/prompts/03_judge.txt:18`, `docs/article.txt:421-425`
- Description: The Phase 4 placeholder stub (written before reading the article carefully) says `"Dimensões (pontuar de 0.0 a 1.0)"`. The article (§8.3) uses an integer scale of 0–10 with explicit thresholds (0–4 insatisfatório, 5–7 aceitável, 8–10 satisfatório) and the approval threshold is stated as ≥70% coverage. Using 0.0–1.0 would change how the threshold logic works and what the Agent 2 schema should enforce.
- Failure scenario: Phase 4 implementer reads the stub comment, writes `agent2_out.json` with `"cobertura": {"type": "number", "minimum": 0.0, "maximum": 1.0}`, but the LLM (following article-derived prompt) outputs `{"cobertura": 8}` — schema validation fails.
- Recommendation: Update `03_judge.txt` placeholder comment to match the article (0–10 integers). Decide and document the score range in `docs/PLAN.md §7` before writing the schema.

### [MEDIUM] FINDING-12: `_section_body` returns empty string silently — LLM receives empty `{domain_glossary}` or `{few_shot_examples}` with no warning
- Status: **OPEN**
- File: `pipeline/agents/agent1_generate.py:112-116`
- Description: If a section title in the blob doesn't match exactly (e.g., a trailing space, unicode difference, or future rename of `REQUIRED_SECTIONS`), `_section_body` returns `""` silently. The agent prompt is constructed with an empty `{domain_glossary}` or `{few_shot_examples}` tag, which degrades generation quality with no error or log.
- Failure scenario: Developer renames a section in `builder.py` from `"Glossário de Domínio"` to `"Glossário"` → agent1 runs successfully with zero domain context → test case quality degrades → no alert in output.
- Recommendation: Raise `AgentOutputError` (or at minimum `warnings.warn`) when `_section_body` finds no matching section. Since both section titles are in `REQUIRED_SECTIONS`, they are guaranteed to exist if the builder ran — so raising is safe.

### [MEDIUM] FINDING-13: `run_phase3` returns `exit_code=1` when stories are legitimately BLOCKED — no distinction between error and gate rejection
- Status: **OPEN**
- File: `pipeline/workflow/runner.py:140`
- Description: `return aggregate, 1 if blocked or errors else 0`. A run where Agent 0 correctly rejects a story (expected behaviour) exits with code 1, the same as a run where an exception occurred. In CI/CD, both would be treated as failures.
- Failure scenario: All 5 stories are processed correctly, 1 is blocked by Agent 0 (the quality gate working as intended). The pipeline exits 1 → CI marks the build as failed.
- Recommendation: Separate exit codes: `exit_code=0` for runs with no exceptions (blocked is acceptable), `exit_code=1` only for unexpected exceptions. Or add a CLI flag `--fail-on-blocked`.

### [MEDIUM] FINDING-14: `gemini-3.1-flash` model name is unverified — error occurs at API call time, not startup
- Status: **OPEN**
- File: `pipeline/settings.py:33`, `pipeline/llm/gemini.py:9`
- Description: `gemini-3.1-flash` appears in `_THINKING_MODELS` and is the default `gemini_model`. As of knowledge cutoff, the Gemini API uses `gemini-2.5-flash` and `gemini-2.5-pro` as current thinking models. If `gemini-3.1-flash` is not a valid API name, `GeminiClient.__init__` succeeds (it only validates the API key), but the first `client.complete()` call fails with an API error that is ambiguous to diagnose.
- Failure scenario: User sets `LLM_PROVIDER=gemini` in `.env`, runs the pipeline, Agent 0 throws an exception on the first API call with `404 Model not found` — printed as a generic error, with no hint that the model name is wrong.
- Recommendation: Verify the model name against current Gemini API availability. Consider adding a `validate_model()` call at client construction time, or adding a startup check in `main()`.

### [MEDIUM] FINDING-15: `run_agent0_all` is dead code — defined but never called from `main()`
- Status: **OPEN**
- File: `pipeline/workflow/runner.py:13-56`
- Description: `run_agent0_all` is a standalone function that runs only Agent 0 across all stories (without Agent 1). It is never called from `main()`, never called from any test, and has no docstring explaining the intent. `run_phase3` (which is called) subsumes its logic.
- Failure scenario: Developer reading the code assumes `run_agent0_all` is used and modifies it; changes don't affect actual pipeline execution.
- Recommendation: Remove or fold into `run_phase3` with a flag. If it's intended as a future debugging aid, add a comment and a corresponding CLI sub-command.

### [LOW] FINDING-16: Article specifies `CA-01` criteria format; implementation uses `CA-01.1` (with sub-number) — format embedded in schemas and not documented
- Status: **OPEN**
- Files: `pipeline/schemas/agent1_out.json:47`, `data/user_stories/US-01.yaml`
- Description: The article writes criteria IDs as `CA-01` (single number). The implementation uses `CA-01.1`, `CA-01.2` (story-number + sub-criterion). This format is embedded in the schema pattern `^CA-[0-9]{2}\.[0-9]+$` and in every YAML file. It's a deliberate improvement (enables multiple criteria per story) but is undocumented in `docs/PLAN.md §decision-log`.
- Recommendation: Add a decision log entry explaining why the sub-criterion format was chosen.

### [LOW] FINDING-17: US-01 has 4 acceptance criteria; article lists 3 for the login story
- Status: **OPEN**
- Files: `data/user_stories/US-01.yaml`, `docs/article.txt`
- Description: CA-01.4 (email format validation → 422) was added during implementation but is not in the article's example for US-01. Since this criterion drives the evaluation oracle (the "golden" human-written test cases), the oracle must explicitly include CA-01.4 or precision/recall calculations will be off.
- Recommendation: Document the CA-01.4 addition in the PLAN and confirm it is reflected in the human oracle golden file before Phase 7 evaluation.

### [LOW] FINDING-18: Agent 0 output schema adds `criterio_id` per problem — not in the article's contract
- Status: **OPEN**
- File: `pipeline/schemas/agent0_out.json:43-46`
- Description: The article's Agent 0 output (§8.1) has no `criterio_id` field per problem. The implementation adds it as a required field, linking each problem to a specific criterion. This is an improvement for traceability, but it's undocumented in the decision log and any Phase 4 judge prompt written verbatim from the article will not reference `criterio_id`.
- Recommendation: Add a decision log entry. Ensure the Phase 4 judge schema and prompt reference `criterio_id` when iterating over problems.

### [LOW] FINDING-19: `runner.py` silently succeeds when `data/user_stories/` is empty or missing
- Status: **OPEN**
- File: `pipeline/workflow/runner.py:76`
- Description: `builder.build_all()` returns `[]` if no YAML files are found. The runner processes 0 stories, prints `{"total": 0, ...}`, and exits 0. In a Docker volume mount failure (or first-run before stories are created), this is indistinguishable from a successful empty run.
- Failure scenario: Docker volume not mounted → `data/user_stories/` appears empty → pipeline exits 0 with no warning → CI marks it green with no tests run.
- Recommendation: Add a check in `run_phase3`: if `len(results) == 0`, log a warning and return exit_code=1 (or at minimum a visible warning message).

### [LOW] FINDING-20: No `__init__.py` in `pipeline/tests/`
- Status: **OPEN**
- File: `pipeline/tests/`
- Description: The test directory has no `__init__.py`. pytest discovers it fine, but IDE imports and `python -m pytest` with certain configurations may behave unexpectedly. Also prevents test files from importing each other as modules.
- Recommendation: Add an empty `__init__.py` for consistency with `pipeline/agents/__init__.py` etc.

### [LOW] FINDING-21: `ClaudeClient` has no retry logic for transient API errors
- Status: **OPEN**
- File: `pipeline/llm/claude.py:34-51`
- Description: `GeminiClient` retries up to 3 times on transient errors (`ServerError`, `TooManyRequests`, etc.). `ClaudeClient` and `OllamaClient` have no retry logic. A transient Anthropic API overload on the first call will abort the entire pipeline run.
- Failure scenario: Anthropic API returns 529 overloaded on one call → exception propagates → that story's test cases are never generated, silently logged as an error.
- Recommendation: Extract retry logic into a shared decorator or utility in `utils.py` and apply it to all three clients.

### [LOW] FINDING-22: `verify.py` `char_count` and `token_estimate` still reference full `blob.text` after FIX-2
- Status: **OPEN**
- File: `pipeline/context/verify.py:23`, `pipeline/context/models.py:67-74`
- Description: `ContextBlob.char_count` and `token_estimate` use `blob.text` (all sections), but Agent 1 now injects `filtered_text` (3 fewer sections). The token estimate shown by the verify CLI is ~30-40% higher than what actually reaches Agent 1's context window. This can mislead prompt budget planning.
- Recommendation: Either update `char_count`/`token_estimate` to reflect the filtered text, or expose both figures (full and filtered) in `VerificationResult`.

---

## Summary table

| # | Severity | Status | Title |
|---|---|---|---|
| 1 | CRITICAL | FIXED | `_validate_strict_gate` logic bug |
| 2 | HIGH | FIXED | `blob.text` double/triple injection |
| 3 | HIGH | FIXED | Backend Docker excluded pytest |
| 4 | MEDIUM | FIXED | `pytest.ini` missing testpaths |
| 5 | HIGH | OPEN | Repair prompt uses `CT-` IDs → schema fails in Phase 4 |
| 6 | HIGH | OPEN | Repair/generation uses `casos_de_teste` field → schema fails in Phase 4 |
| 7 | HIGH | OPEN | `tipo` enum 3 vs 5 values — Phase 4 repair will be rejected |
| 8 | HIGH | OPEN | Phase 6 network conflict (`network_mode: host` vs bridge hostnames) |
| 9 | MEDIUM | OPEN | Missing backend test for CA-01.4 (invalid email → 422) |
| 10 | MEDIUM | OPEN | Matrix `casos` allows empty array — traceability invariant not enforced |
| 11 | MEDIUM | OPEN | Judge score range mismatch: stub says 0–1, article says 0–10 |
| 12 | MEDIUM | OPEN | `_section_body` returns `""` silently — silent quality degradation |
| 13 | MEDIUM | OPEN | `exit_code=1` for legitimate blocking conflates errors with gate behaviour |
| 14 | MEDIUM | OPEN | `gemini-3.1-flash` model name unverified |
| 15 | MEDIUM | OPEN | `run_agent0_all` dead code |
| 16 | LOW | OPEN | `CA-01.1` format diverges from article `CA-01` — undocumented |
| 17 | LOW | OPEN | CA-01.4 added beyond article scope — oracle alignment unclear |
| 18 | LOW | OPEN | `criterio_id` field added to Agent 0 schema — undocumented |
| 19 | LOW | OPEN | Runner silently succeeds with 0 stories |
| 20 | LOW | OPEN | No `__init__.py` in `pipeline/tests/` |
| 21 | LOW | OPEN | `ClaudeClient` has no retry logic |
| 22 | LOW | OPEN | `char_count`/`token_estimate` reflect full blob, not filtered context |

---

## Priority recommendation for next session

**Before starting Phase 4:**
1. Resolve FINDING-5, -6, -7 — these three together make verbatim adoption of the article's Phase 4 prompts impossible. Decide: adopt TC-format + `casos` in new prompts (recommended), or update schema to CT-format.
2. Add the `minItems: 1` fix for the matrix `casos` array (FINDING-10) — one-line schema change.
3. Fix `03_judge.txt` score range to match article (FINDING-11) — informs schema design.

**Quick wins (< 30 min each):**
- FINDING-9: Add missing CA-01.4 backend test
- FINDING-15: Remove `run_agent0_all` dead code
- FINDING-19: Add empty-stories guard in runner
- FINDING-20: Add `pipeline/tests/__init__.py`
