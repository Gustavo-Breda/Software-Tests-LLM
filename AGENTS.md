# AGENTS.md

Guidance for AI coding agents (Claude Code, Cursor, Copilot, etc.) working in
this repository. Humans: see [`README.md`](./README.md) for the project overview
and [`docs/PLAN.md`](./docs/PLAN.md) for the full roadmap and data contracts.

> **Repo stage:** Phase 0 complete. Phase 1 (PoC web app) in progress.
> The target layout is partially scaffolded — always verify a path exists before
> editing or running it.

---

## What this project is

A GenAI pipeline that converts user stories + acceptance criteria into reviewed
test cases and executable Selenium/PyTest scripts. Six components: Agents 0–3,
a Context Builder, and a Summarizer, plus a proof-of-concept FastAPI + React web
app to test against.

**Two meanings of "agent" — do not confuse them:**
- **Pipeline agents** = the LLM stages (Agent 0–3, Summarizer). These are the
  *product*. Each is driven by a versioned prompt in `pipeline/prompts/`.
- **Coding agents** = you, working on this repo. This file is for you.

---

## How to work in this repo (step-by-step)

Follow this order every session:

1. **Read this file and `docs/PLAN.md`** before writing any code.
2. **Check the current phase** in `docs/PLAN.md §5` — only work on tasks in the
   active phase unless told otherwise.
3. **Verify paths exist** before editing. Many directories in the target layout
   are not yet scaffolded. If a directory is missing, create it per the plan
   rather than guessing.
4. **Run everything through Docker.** No host Python/Node required. Use
   `docker compose run --rm pipeline <cmd>` for pipeline work.
5. **Before modifying any agent I/O contract:** update the matching schema in
   `pipeline/schemas/` and the contract table in `docs/PLAN.md §7`.
6. **After any structural change:** keep `docs/PLAN.md`, `AGENTS.md`, and
   `README.md` in sync.
7. **Never commit `.env` or API keys.** Use `.env.example` as the only template.

### Before creating a file or directory

- Check `docs/PLAN.md §4` for the canonical target layout.
- Confirm the parent directory exists before creating children.
- Follow naming from the plan, not from inference.

### Before calling an LLM from pipeline code

- Confirm `LLM_PROVIDER` and `LLM_MODEL` are set in `.env` or passed explicitly.
- Use `pipeline/llm/factory.py → get_client(f"{provider}:{model}", settings)`.
- Never hardcode provider/model names in pipeline business logic.

### Before opening a PR / committing

- `.env` must never appear in `git status`.
- If a new env var is added, add it to `.env.example` with an empty value.
- If a prompt or schema changed, update the contract table in `docs/PLAN.md §7`.

---

## Current state

| Component | Status |
|---|---|
| Docker stack (`ollama`, `pipeline`, `backend`, `frontend`) | ✅ Phase 0 done |
| LLM client layer (`pipeline/llm/`) | ✅ Phase 0 done |
| Settings & env loader (`pipeline/settings.py`) | ✅ Phase 0 done |
| Workflow runner stub (`pipeline/workflow/runner.py`) | ✅ Phase 0 done |
| PoC backend — FastAPI (`app/backend/`) | 🔧 Stub only — Phase 1 |
| PoC frontend — React (`app/frontend/`) | 🔧 Scaffold only — Phase 1 |
| Pipeline agents 0–3, Summarizer | ❌ Phase 3–5 |
| Context builder, glossary, ui_map | ❌ Phase 2 |
| Prompts (`pipeline/prompts/`), schemas (`pipeline/schemas/`) | ❌ Phase 3+ |
| Evaluation harness (`evaluation/`) | ❌ Phase 7 |

---

## Project structure

```
pipeline/              # the QA assistant pipeline (Python)
  agents/              # agent0–3 + summarizer (Phase 3–5, not yet scaffolded)
  context/             # context_builder.py, glossary.md, ui_map.json (Phase 2)
  llm/                 # provider-agnostic LLM clients
    adapter.py         # base class + LLMResponse dataclass
    factory.py         # get_client("provider:model", settings)
    claude.py          # Anthropic Claude client
    gemini.py          # Google Gemini client (thinking-model support)
    ollama_client.py   # Ollama client (OpenAI-compatible local models)
  prompts/             # one .txt per agent — Phase 3+, not yet created
  schemas/             # JSON schemas per agent I/O — Phase 3+
  workflow/
    runner.py          # entry point; reads LLM_PROVIDER/LLM_MODEL from env
  settings.py          # configuration loader (reads .env)
app/
  backend/             # FastAPI PoC app (Phase 1 — stub)
  frontend/            # React PoC app (Phase 1 — scaffold)
data/                  # user_stories/ (inputs), golden/ (oracle) — not yet
generated/             # pipeline outputs (test_cases/, scripts/, reports/) — not yet
evaluation/            # metrics.py + results/ — Phase 7
docker/                # Dockerfiles: pipeline, backend, frontend, ollama
docker-compose.yml     # services: ollama, pipeline, backend, frontend, selenium
.env.example           # all env vars with empty values — the only committed template
docs/
  PLAN.md              # full roadmap, data contracts, decision log
  REFERENCES.md
  article.pdf          # source report — do not delete or rewrite
```

---

## Environment & setup

The full stack runs in Docker. No host Python/Node needed.

| Service | Port | Purpose |
|---|---|---|
| `ollama` | 11434 | Local open models (Llama, Qwen, DeepSeek, Mistral…) |
| `pipeline` | — | Pipeline runner + generated tests |
| `backend` | 8001 | FastAPI PoC app |
| `frontend` | 5173 | React PoC app |
| `selenium` | 4444 | Browser for generated tests (commented out until Phase 6) |

**Switching LLM provider:** set `LLM_PROVIDER` and `LLM_MODEL` in `.env`.

| `LLM_PROVIDER` | Required key | Notes |
|---|---|---|
| `ollama` | none | Model pulled automatically on container start |
| `gemini` | `GOOGLE_API_KEY` | |
| `claude` / `anthropic` | `ANTHROPIC_API_KEY` | |

```bash
# Build & start the full stack
docker compose up -d --build

# Run the pipeline (reads LLM_PROVIDER/LLM_MODEL from .env)
docker compose run --rm pipeline python -m pipeline.workflow.runner

# Override provider inline without editing .env
docker compose run --rm \
  -e LLM_PROVIDER=gemini \
  -e LLM_MODEL=gemini-2.5-flash \
  pipeline python -m pipeline.workflow.runner

# Pull an open model into the ollama service (first run)
docker compose exec ollama ollama pull llama3.1

# Run generated tests
docker compose run --rm pipeline pytest generated/scripts

# Compute evaluation metrics
docker compose run --rm pipeline python -m evaluation.metrics

# Tear down
docker compose down
```

---

## Conventions

### LLM / pipeline
- **Prompts live in files** under `pipeline/prompts/`, one per agent, versioned.
  Never inline large prompts in code.
- **Outputs are strict JSON** — no prose outside the JSON block. Validate every
  agent output against its schema in `pipeline/schemas/` before passing downstream.
- **Provider-agnostic client.** Always instantiate via
  `factory.get_client(f"{provider}:{model}", settings)`. Models/keys are config,
  never hardcoded in business logic.
- **Bounded repair loop.** The Agent 2 → Agent 1 repair branch must respect a max
  iteration count (`N`) to avoid infinite loops.
- **Traceability is mandatory.** Every test case maps to ≥1 acceptance criterion
  (`criterios_cobertos`); keep the traceability matrix in sync.

### Generated automation code (Agent 3 output rules)
- Python + PyTest + Selenium.
- **Page Object Model:** each screen is a class in `pages.py`; no raw selectors
  inside test functions.
- **Prefer `data-testid`** selectors; fall back to CSS/XPath only when absent.
  Never invent selectors — record gaps in `pendencias_de_automacao`.
- **No `time.sleep()`** — use `WebDriverWait` with explicit conditions.
- One test function per case: `test_{id}_{short_desc}`, with a comment stating
  the case ID and objective. Test data from fixtures/JSON, not hardcoded.

### PoC web app (`app/`)
- Tag **every interactive element with `data-testid`** from day one.
- Keep `pipeline/context/ui_map.json` in sync whenever selectors change.
- Business rules must be explicit and testable (e.g., 60s lockout after 5 failed
  logins; field-length validations). Match the acceptance criteria in the report.

### General code style
- Code and identifiers in **English**; user-facing strings and JSON contracts in
  Portuguese (e.g., `criterios_cobertos`, `passos`, `resultado_esperado`).
- Small, composable functions per agent — no monoliths.
- No comments explaining *what* the code does; only *why* for non-obvious
  invariants, constraints, or workarounds.

---

## Secrets & configuration

- `.env` is git-ignored — never commit it.
- `.env.example` has no real values — update it when adding new env vars.
- `docker-compose.yml` injects `.env` into every service automatically.
- `LLM_PROVIDER` + `LLM_MODEL` select the active model for the pipeline runner.
- Open models via Ollama need no API key: set `LLM_PROVIDER=ollama`.

---

## Do / Don't

**Do**
- Read `docs/PLAN.md` before implementing — phases, contracts, and the decision
  log are there.
- Keep prompts, schemas, and docs in sync when contracts change.
- Record open decisions (model, orchestration, `N`) in the `docs/PLAN.md`
  decision log.
- Add `data-testid` to every interactive element in the PoC app from the start.

**Don't**
- Don't delete or rewrite `docs/article.pdf` (the source report).
- Don't commit generated artifacts as source unless explicitly asked.
- Don't add heavy dependencies/frameworks without recording the rationale in
  `docs/PLAN.md`.
- Don't bypass verification gates (judge, human approval) in the pipeline flow.
- Don't hardcode LLM provider or model names in pipeline business logic.
