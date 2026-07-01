# Implementation Plan — QA Assistant Agent

This plan turns the AV1 report into a buildable project. It defines scope, the
target architecture, open technical decisions, a phased roadmap with milestones,
the data contracts between agents, and the evaluation methodology.

> Companion docs: [`README.md`](../README.md) (overview) and
> [`AGENTS.md`](../AGENTS.md) (how coding agents should work in this repo).

---

## 1. Goal & Scope

**Goal.** Build and evaluate an automated, GenAI-supported pipeline that takes a
user story in natural language (with acceptance criteria), generates functional
test cases, semantically validates them, and translates them into executable
Selenium/PyTest scripts against a proof-of-concept web app — ending in a
coverage report.

**In scope**
- The 6-component pipeline (Agents 0–3, Context Builder, Summarizer) + repair loop.
- A PoC web app (FastAPI + React) covering 5 user stories.
- A human oracle (gabarito) and an evaluation harness for the metrics in Section 8.

**Out of scope**
- Production-grade scale, multi-tenant systems, or CI/CD integration of the pipeline.
- Replacing the human analyst — humans review, approve, or reject at the gates.

---

## 2. Architecture (recap)

Sequential pipeline with a repair branch. Two invariants:
1. **No artifact advances without verification** — test cases pass Agent 2
   before becoming code; scripts pass human review before execution.
2. **The human never writes from scratch** — they review/approve/reject.

```
User Story + AC
  → Agent 0 (quality gate)  ──needs clarification──▶ human refines ──┐
        │ approved                                                   │
        ▼                                                            │
  Context Builder  ◀───────────────────────────────────────────────┘
        ▼
  Agent 1 (test-case generation, JSON)
        ▼
  Agent 2 (LLM-as-a-Judge) ──rejected (≤ N retries)──▶ Repair → Agent 1
        │ approved
        ▼
  Human review & approval
        ▼
  Agent 3 (Selenium/PyTest codegen)
        ▼
  Execute  →  Summarization Agent  →  Coverage/Execution Report
```

See `README.md` for the per-agent responsibility table.

---

## 3. Open Technical Decisions

Per the report, the **model and orchestration framework are intentionally
deferred** to implementation, chosen by cost, latency, instruction-following,
and team access. The architecture, prompts, and inter-agent flow are
**model-independent**. Track decisions here as they are made.

### 3.1 LLM model / provider — candidates

The pipeline runs through a **provider-agnostic client**, so models are swapped
via config (`.env`: `LLM_PROVIDER`, `LLM_MODEL`). Two provider families:

**Closed (API):**
| Option | Pros | Cons / risks |
|---|---|---|
| GPT-5 (or current OpenAI flagship) | Strong instruction-following, JSON mode | Cost; API quotas; proprietary dependency |
| Claude Sonnet 4.6 | Strong on long structured prompts, reliable JSON | Cost; access |
| Gemini 3.1 Flash | Thinking-model support; large context, competitive cost | Variable JSON adherence |

**Open (local, via Ollama):**
| Option | Pros | Cons / risks |
|---|---|---|
| Llama 3.1 / Qwen2.5 / DeepSeek / Mistral | No API cost or vendor lock-in; runs offline; addresses the "last-mile"/industrial-readiness gap (Gheventer et al.) | Weaker instruction-following & JSON adherence; needs local compute (GPU helps) |

> Ollama serves an **OpenAI-compatible API** (`http://ollama:11434/v1`), so the
> same client code reaches both families — only `.env` changes. Running open
> models locally lets us **compare closed vs. open** on the same stories, a
> direct test of Gheventer et al.'s industrial-readiness concern (see Section 8).

> Note (Silva et al. 2026): A controlled study with GPT-4o, DeepSeek, and Gemini 1.5 Flash
> on 10 real user stories found a **performance plateau** — no statistically significant
> difference between models in F1-Score (range 0.58–0.65, zero-shot). Model choice should
> be guided by cost and latency rather than expected quality difference. One-shot prompting
> improves precision but increases omissions vs. zero-shot; neither dominates in F1.
> The dominant failure mode is **omission** (FN), not incorrect content. Compensate with
> structured domain context, explicit acceptance criteria, and the multi-stage judge+repair loop.

### 3.2 Orchestration — candidates
| Option | Pros | Cons / risks |
|---|---|---|
| Plain Python + direct SDK | Minimal deps, full control, easy to debug for a PoC | Manual state/branch handling |
| LangGraph / agent framework | Explicit state graph, built-in branching/retries | Extra dependency & learning curve |

**Decision rule:** start with the lightest approach that supports the repair
branch and bounded retries; introduce a framework only if state handling becomes
unwieldy. **Status: TBD — record the choice here once made.**

### 3.3 Other decisions to record
- Max repair iterations `N`: **3** — sufficient to correct systematic IncorrectFact/Omission
  patterns observed by Silva et al. (2026) without risk of infinite loops.
- Multi-candidate generation: **Deferred** — Silva et al. found no statistically significant
  gain from any single prompting variation; invest effort in prompt design and RAG context
  rather than multi-candidate overhead. (Best-of-N via Wang et al./CURE remains a stretch goal.)
- JSON validation strategy (schema lib vs. hand-rolled).

---

## 4. Repository Layout (target)

```
pipeline/
  agents/
    agent0_quality_gate.py
    agent1_generate.py        # also used for repair
    agent2_judge.py
    agent3_codegen.py
    summarizer.py
  context/
    models.py                 # UserStory, ContextSection, ContextBlob
    builder.py                # ContextBuilder + REQUIRED_SECTIONS
    verify.py                 # VerificationResult + verify_complete()
    context_builder.py        # CLI: python -m pipeline.context.context_builder
    verify_context_builder.py # CLI: verify all stories
    glossary.md               # domain glossary (human-authored)
    ui_map.json               # screen → data-testid selectors (human-authored)
    examples/                 # approved few-shot examples (.json)
  llm/                        # provider-agnostic LLM clients (factory + providers)
    adapter.py
    claude.py
    factory.py
    gemini.py
    ollama_client.py
  prompts/
    01_quality_gate.txt
    02_generate.txt
    03_judge.txt
    04_repair.txt
    05_codegen.txt
    06_summarize.txt
  schemas/                    # JSON schema / models per agent I/O
  workflow/                   # orchestrator of pipeline steps
    runner.py
  settings.py                 # configuration loader
app/
  backend/                    # FastAPI
  frontend/                   # React
data/
  user_stories/               # US-01..US-05 as structured input
  golden/                     # human oracle (expected test cases)
generated/
  test_cases/  scripts/  reports/
evaluation/
  metrics.py                  # precision/recall/F1, judge precision/recall, etc.
  results/
docker/
  Dockerfile.backend
  Dockerfile.frontend
  Dockerfile.ollama
  Dockerfile.pipeline
docker-compose.yml            # services: ollama, pipeline, backend, frontend, selenium
.env.example                  # LLM_PROVIDER/LLM_MODEL + API keys (no secrets)
docs/
  REFERENCES.md             # cited papers + verification notes
  article.pdf               # source report (do not delete)
```

---

## 5. Roadmap & Milestones

Phases are ordered to unblock dependencies (the PoC app and context assets must
exist before scripts can run). Each phase lists deliverables and a done-check.

### [x] Phase 0 — Setup & decisions (Docker)
- [x] Author `docker-compose.yml` + Dockerfiles for `ollama`, `pipeline`, `backend`, `frontend`, `selenium`; `docker compose up -d --build` brings the stack up.
- [x] Add `.env.example` (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, optional API keys); keep `.env` git-ignored.
- [x] Record Section 3 decisions (provider/model, orchestration, `N`) as they are made.
- [x] Provide **≥1 closed model** (API key) **and ≥1 open model** (`docker compose exec ollama ollama pull <model>`) so both can be benchmarked.
- [x] **Done when:** `docker compose run --rm pipeline` successfully executes a test query against the local `ollama` service (e.g. Llama 3) and verifies client setup.

### [x] Phase 1 — Proof-of-Concept web app
- [x] FastAPI backend: auth, register, create/list/filter/cancel requests; 60s lockout after 5 failures; field-length validations; JWT + bcrypt; SQLite with `RESET_DB_ON_STARTUP`. Poetry for deps. Pytest suite: 21 tests covering US-01..US-05 (SQLAlchemy 2.0, Pydantic v2).
- [x] React frontend with `data-testid` on every interactive element; React Router v6; AuthProvider context; typed fetch layer with `ApiError` class. pnpm + Vite.
- [x] Backend and frontend run as `docker compose` services.
- [x] Seed/test data that is stable and reproducible (seeded on container start).
- [x] `pipeline/context/ui_map.json` created with all selectors documented.
- [ ] **Done when:** `docker compose up` serves all 5 flows end-to-end.

### [x] Phase 2 — Context assets & Context Builder
- [x] Author `glossary.md` and `ui_map.json` (screen map + selectors) for the PoC.
- [x] Implement `context_builder.py` to assemble glossary, approved examples, screen map, and selectors into prompt context (RAG-style injection).
- [x] **Done when:** Context Builder produces a complete context blob for each story.

### [ ] Phase 3 — Agents 0 & 1
- [ ] Implement Agent 0 (quality gate) and Agent 1 (test-case generation) with the prompts in Section 7; enforce JSON-only outputs validated against schemas.
- [ ] **Done when:** the 5 stories pass Agent 0 (or produce actionable clarifications) and Agent 1 emits valid structured test cases with a traceability matrix.

### [ ] Phase 4 — Agent 2 (judge) + repair loop
- [ ] Implement Agent 2 (LLM-as-a-Judge) scoring coverage, fidelity, clarity, automatability; route rejected cases back through Agent 1 (repair prompt) with bounded retries `N`.
- [ ] **Done when:** rejected cases are repaired and re-judged; loop terminates within `N`.

### [ ] Phase 5 — Agent 3 (codegen)
- [ ] Implement Agent 3: generate `conftest.py`, `pages.py`, `test_*.py` using Page Object Model, `data-testid` selectors, `WebDriverWait` (no `time.sleep`). Record unresolved selectors in `pendencias_de_automacao`.
- [ ] **Done when:** generated scripts import and collect under PyTest without syntax errors.

### [ ] Phase 6 — Summarizer & execution
- [ ] Run generated scripts against the PoC; feed PyTest output + Selenium logs + error evidence into the Summarization Agent.
- [ ] **Done when:** a coverage/execution report classifies each failure cause and maps coverage per acceptance criterion.

### [ ] Phase 7 — Evaluation
- [ ] Build the human oracle (gabarito) for the 5 stories.
- [ ] Implement `evaluation/metrics.py` and compute all Section 8 metrics.
- [ ] Record perceived-effort timings (pipeline review vs. manual authoring).
- [ ] **Done when:** a metrics table is produced and reproducible.

### [ ] Phase 8 — Final report (AV2)
- [ ] Consolidate results, compare with Silva et al., document limitations.

---

## 6. Human-in-the-loop responsibilities

The pipeline reduces mechanical work, not responsibility. Humans:
1. Write/review user stories & acceptance criteria before feeding the pipeline.
2. Author the glossary and UI map for the PoC.
3. Review Agent 0 alerts and decide whether a story advances.
4. Approve/reject test cases after the judge.
5. Review generated scripts before execution.
6. Execute scripts and compare results against a human oracle.
7. Record limitations, errors, and learnings.

---

## 7. Prompts & Data Contracts

Each agent uses a versioned prompt file under `pipeline/prompts/`. The report
contains the initial prompt text for all six (quality gate, generation, judge,
repair, codegen, summarize) — port them verbatim as the v1 baseline, then
iterate. **Outputs are strict JSON, no prose outside the JSON.**

Key contracts (fields summarized; mirror the report exactly in `schemas/`):

- **Agent 0 →** `{ status, derivavel, observacao_formato, problemas[], recomendacao }`
- **Agent 1 →** `{ test_cases[]{ id, titulo, objetivo, criterios_cobertos[], tipo,
  prioridade, pre_condicoes[], dados_de_teste{}, passos[], resultado_esperado,
  automatizavel, observacoes }, matriz_rastreabilidade[], alertas[] }`
- **Agent 2 →** `{ status_geral, pontuacao{cobertura, fidelidade_ao_requisito,
  clareza, automatizabilidade}, casos_aprovados[], casos_reprovados[],
  problemas[], cenarios_omitidos_sugeridos[], decisao }`
- **Repair →** Agent 1 contract + `correcao_aplicada` per case.
- **Agent 3 →** `{ arquivos{ "conftest.py", "pages.py", "test_*.py" },
  pendencias_de_automacao[] }`
- **Summarizer →** `{ resumo{}, falhas[], cobertura_por_criterio[],
  alertas_de_qualidade[], proximos_passos[] }`

**Agent 0 rubric → INVEST.** Cross-reference Agent 0's quality checks with the
INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable)
so the gate traces cleanly to Hernández-Agüero et al. and Quattrocchi et al.
(both show LLMs assess story quality reliably given a defined criteria framework).

**Codegen rules (Agent 3):** PyTest + Selenium; Page Object Model (no raw
selectors in test functions); prefer `data-testid`; `WebDriverWait` with explicit
conditions; one `test_{id}_{desc}` per case with an ID/objective comment; test
data from fixtures/JSON, not hardcoded.

---

## 8. Evaluation Metrics

Combine quantitative metrics with qualitative defect analysis (Silva et al.
methodology) for direct comparison.

**Test-case quality**
- Precision — generated cases judged correct by the human oracle.
- Recall — oracle-expected cases covered by the pipeline.
- F1 — harmonic mean of precision & recall.
- Omission rate — expected scenarios not generated.
- Incorrect-fact rate — cases assuming business rules absent from the story/criteria.
- Acceptance-criteria coverage — % of criteria with ≥1 approved associated case.

**Automation quality**
- Executable-scripts rate — % running without syntax/selector errors.
- Functional success rate — % passing when the feature is correct in the system.

**Pipeline-component efficacy**
- Judge precision — % of judge-reported problems confirmed by human review.
- Judge recall — % of human-found problems the judge also detected.
- Perceived effort — analyst review time vs. manual authoring time for the same stories.

**Methodology notes**
- *Silva et al. (2026) baseline established.* Their metrics are Precision, Recall, and F1-Score
  computed against a human-expert oracle using the Travassos et al. (1999) defect taxonomy
  (IncorrectFact, Inconsistency, Ambiguity, Omission). Correctness is **all-or-nothing**: one
  defect in a multi-step case makes the entire case Defective. The bare Agent 1 baseline in
  this project (zero/one-shot, no RAG, no judge) **replicates Silva et al.'s protocol** — use
  identical oracle construction (domain experts, production-validated) and the same three
  metrics for direct comparison. Expected baseline: Precision ~0.72, Recall ~0.56, F1 ~0.62
  (zero-shot). Replication package: https://github.com/leonardocesarc/testcase
- *Selector strategy grounded in Souza et al. (2025)*: a 10-year experience report on Selenium
  automation in a Brazilian legal system identified "random generation of form element identifiers"
  as one of the three primary barriers to test automation. The `data-testid` convention adopted
  throughout this project is the prescribed solution to that antipattern.
- *Apples-to-apples:* also run a **bare Agent 1 baseline** (zero/one-shot, no
  RAG, no judge) so the full pipeline can be compared against a Silva-style
  single-prompt baseline (ablation).
- *Incorrect-fact rate:* denominator = all generated cases; measure **both
  pre- and post-repair** to show the repair loop's effect.
- *Judge precision/recall:* stratify by case type (positive / negative / edge)
  so easy positive cases can't inflate the score (cf. DAJ distribution-shift findings).
- *Closed vs. open models:* run the full pipeline with ≥1 closed model and ≥1
  open model (via Ollama) on the same stories; report all Section 8 metrics per model —
  a direct test of Gheventer et al.'s industrial-readiness concern.

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Plausible-but-incorrect outputs | Quality gate + judge + repair loop; human approval gate |
| Judge approves bad cases / rejects good ones (style bias) | Score per dimension; evidence-based decisions; measure judge precision/recall |
| Fragile selectors break scripts | `data-testid` from day one; maintain `ui_map.json`; Page Object Model |
| Story quality determines output quality | Agent 0 gate before any generation |
| Model lock-in / access issues | Provider-agnostic `llm_client`; keep prompts model-independent |
| API version instability / model drift | Pin exact model versions in `.env.example`; lock Ollama model tags; run baseline before updating model version (Gheventer et al. 2026 cite Kang et al. 2024: silent GPT-3.5 updates broke output format and automated pipelines) |
| Repair loop non-termination | Bounded retries `N = 3` |

---

- [x] LLM provider(s) + model(s) chosen (closed API and/or open via Ollama): Ollama (Llama 3) for local open model, Gemini 3.1 Flash/Claude Sonnet 4.6 for closed models — rationale: Swappable via `.env`, allowing local vs. closed model comparison.
- [x] Active provider/model selection: `LLM_PROVIDER` + `LLM_MODEL` env vars select the active provider at runtime; `pipeline/workflow/runner.py` reads these and calls `factory.get_client()` — no code changes needed to switch models.
- [x] Orchestration approach chosen: Plain Python script (`pipeline/workflow/runner.py`) — rationale: Keeps dependencies light and provides maximum control.
- [x] Max repair iterations `N`: **3** — grounded in Silva et al. (2026) failure-mode analysis (IncorrectFact/Omission patterns correctable in ≤3 cycles)
- [x] Multi-candidate generation: **Deferred** — no significant gain observed across prompting variations in Silva et al.; out of scope for AV2.
- [x] JSON validation approach: `jsonschema` (from requirements.txt)
- [x] Context Builder design (Phase 2): (1) Filter aggressively per story — each blob only includes the screens and endpoints that story actually touches; the full ui_map would inflate the blob ~50% without benefit. (2) Include the full glossary (~5 KB) in every blob — it is compact and coeso; splitting by story would create inconsistency risk. (3) Single few-shot example per blob — more examples increase tokens without clear marginal gain; story-specific examples can be added if coverage gaps appear. (4) Section order: glossary → API → UI → seed → example → story — LLM loads all vocabulary before reading the task (rationale: Correia et al., 2025 on RAG verbosity risk).

**Pending source materials** (upload to [`docs/`](./)):
- [x] Silva et al. — uploaded as `docs/Todos e Tema 2- Silva et al., 2026.pdf` (content not yet cross-referenced — requires pdfplumber extraction)
- [x] Gheventer et al. — uploaded as `docs/Todos- Gheventer et al., 2026.pdf` (SLR; Kitchenham procedures; tools: Copilot, Snyk, Testim, GitLab Duo; Cohen's Kappa for inter-rater agreement)
- [x] Souza et al. — uploaded as `docs/Tema 2- de Souza et al., 2025.pdf` (backs `data-testid` strategy)
- [ ] Hernández-Agüero et al. (also needs a DOI/URL)
