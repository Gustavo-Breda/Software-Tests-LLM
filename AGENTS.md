# AGENTS.md

Guidance for AI coding agents (Claude Code, Cursor, etc.) working in this
repository. Humans: see [`README.md`](./README.md) for the project overview and
[`plan.md`](./plan.md) for the roadmap and data contracts.

> **Repo stage:** early. The structure below is the *target* layout from
> `plan.md`; many directories do not exist yet. When scaffolding, follow it.
> Keep this file updated as the build progresses.

---

## What this project is

A GenAI pipeline that converts user stories + acceptance criteria into reviewed
test cases and executable Selenium/PyTest scripts. It is made of six components
(Agents 0–3, a Context Builder, and a Summarizer) plus a proof-of-concept web
app to test against. **Do not confuse the two meanings of "agent":**

- **Pipeline agents** = the LLM stages (Agent 0–3, Summarizer). These are the
  *product*. Each is driven by a versioned prompt in `pipeline/prompts/`.
- **Coding agents** = you, working on this repo. This file is for you.

---

## Project structure

```
pipeline/      # the QA assistant pipeline (Python)
  agents/      # agent0_quality_gate, agent1_generate (+repair), agent2_judge,
               # agent3_codegen, summarizer
  context/     # context_builder.py, glossary.md, ui_map.json
  prompts/     # one .txt per agent — the v1 prompts come from the AV1 report
  schemas/     # JSON schemas / models for agent inputs & outputs
  llm_client.py# provider-agnostic LLM wrapper (model is swappable)
  pipeline.py  # orchestration + repair branch + retry limit
poc-app/
  backend/     # FastAPI
  frontend/    # Angular
data/          # user_stories/ (inputs), golden/ (human oracle)
generated/     # pipeline outputs: test_cases/, scripts/, reports/
evaluation/    # metrics.py + results/
references/    # cited papers + verification notes
docker/        # Dockerfiles: pipeline, backend, frontend
docker-compose.yml  # services: ollama, pipeline, backend, frontend, selenium
.env.example   # LLM_PROVIDER/LLM_MODEL + API keys (no secrets)
```

---

## Environment & setup

This project runs in **Docker** — no host Python/Node toolchain required. Every
service is a container orchestrated by `docker-compose.yml`:

| Service | Image / build | Purpose |
|---|---|---|
| `ollama` | `ollama/ollama` | Local server for **open models** (Llama, Qwen, DeepSeek, Mistral…) on port 11434 |
| `pipeline` | `docker/pipeline.Dockerfile` | Runs the agents + the generated PyTest/Selenium tests |
| `backend` | `docker/backend.Dockerfile` | FastAPI PoC backend |
| `frontend` | `docker/frontend.Dockerfile` | Angular PoC frontend |
| `selenium` | `selenium/standalone-chromium` | Browser for executing generated tests |

- **Host:** any OS with Docker (Windows uses Docker Desktop + WSL2). All commands
  below are cross-platform — no PowerShell-specific syntax needed.
- **Models:** closed providers (Anthropic/OpenAI/Google) are reached via API keys
  in `.env`; open models run locally via the `ollama` service (no key needed).
- The LLM client is **provider-agnostic** — switch via `.env` (`LLM_PROVIDER`,
  `LLM_MODEL`), no code changes (see `plan.md` §3.1).

> Commands below are the *intended* workflow. Verify a service/script exists
> before running; if it doesn't yet, scaffold it per `plan.md` rather than guessing.

```bash
# Build & start the full stack
docker compose up -d --build

# Pull an open model into the ollama service (first run only)
docker compose exec ollama ollama pull llama3.1

# Run the pipeline on a user story
docker compose run --rm pipeline python -m pipeline.pipeline --story data/user_stories/US-01.json

# Run generated Selenium/PyTest scripts (against the selenium + backend services)
docker compose run --rm pipeline pytest generated/scripts

# Compute evaluation metrics
docker compose run --rm pipeline python -m evaluation.metrics

# Tear down
docker compose down
```

> Need to extract text from `article.pdf`? Run it in a container too:
> `docker compose run --rm pipeline python -c "from pypdf import PdfReader; ..."`

---

## Conventions

### LLM / pipeline
- **Prompts live in files** under `pipeline/prompts/`, one per agent, versioned.
  Do not inline large prompts in code. The v1 text is in the AV1 report (§8).
- **Outputs are strict JSON** — no prose outside the JSON. Validate every agent
  output against its schema in `pipeline/schemas/` before passing it downstream.
- **Keep the LLM client provider-agnostic.** Support both API providers
  (Anthropic/OpenAI/Google) and local **open models via Ollama**; pick with
  `LLM_PROVIDER`/`LLM_MODEL` in `.env`. The pipeline must not bet on one model
  (see `plan.md` §3.1). Models/keys are config, never hardcoded.
- **Bounded repair loop.** The Agent 2 → Agent 1 repair branch must respect a max
  iteration count (`N`) to avoid infinite loops.
- **Traceability is mandatory.** Every test case maps to ≥1 acceptance criterion
  (`criterios_cobertos`); keep the traceability matrix in sync.

### Generated automation code (Agent 3 output rules — enforce these)
- Python + PyTest + Selenium.
- **Page Object Model:** each screen is a class in `pages.py`; no raw selectors
  inside test functions.
- **Prefer `data-testid`** selectors; use CSS/XPath only when no `data-testid`
  exists in the UI map. **Never invent selectors** — record gaps in
  `pendencias_de_automacao`.
- **No `time.sleep()`** — use `WebDriverWait` with explicit conditions.
- One test function per case: `test_{id}_{short_desc}`, with a comment stating
  the case ID and objective. Test data comes from fixtures/JSON, not hardcoded.

### PoC web app
- Tag **every interactive element with `data-testid`** from the start; keep
  `pipeline/context/ui_map.json` in sync with the UI. Selector drift silently
  breaks generated scripts.
- Keep business rules explicit and testable (e.g., 60s lockout after 5 failed
  logins; field-length bounds). Match the acceptance criteria in the report.

### General code style
- Match the conventions of surrounding code; keep changes minimal and focused.
- Prefer small, composable functions per agent over a monolith.
- Write code and identifiers in **English**; user-facing strings in the PoC and
  the JSON contracts follow the report (Portuguese field names like
  `criterios_cobertos`, `passos`, `resultado_esperado` — keep them as specified).

---

## Secrets & configuration

- Configuration lives in `.env` (git-ignored); ship `.env.example` with no real
  values. `docker-compose.yml` injects it into the services.
- **Never commit API keys.** Closed-provider keys (`ANTHROPIC_API_KEY`,
  `OPENAI_API_KEY`, `GOOGLE_API_KEY`) belong in `.env` only.
- **Open models via Ollama need no key** — set `LLM_PROVIDER=ollama` and
  `LLM_BASE_URL=http://ollama:11434/v1` (Ollama serves an OpenAI-compatible API).
- Select the active model with `LLM_PROVIDER` + `LLM_MODEL` so closed and open
  models are swappable without code changes.

---

## Do / Don't

**Do**
- Read `plan.md` before implementing — it has phases, contracts, and the decision log.
- Keep prompts, schemas, and the README/plan in sync when contracts change.
- Record open decisions (model, orchestration, `N`) in the `plan.md` decision log.

**Don't**
- Don't delete or rewrite `article.pdf` (the source report).
- Don't commit generated artifacts as if they were source unless asked.
- Don't add heavy dependencies/frameworks without recording the rationale in `plan.md`.
- Don't bypass the verification gates (judge, human approval) in the pipeline flow.
