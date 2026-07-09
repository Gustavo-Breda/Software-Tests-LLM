# Implementation Notes — Phase 6 + Selenium Infrastructure

> Data: 2026-07-09  
> Branch: main  
> Revisão: sênior → júnior aplicada antes da implementação (ver histórico de conversa).

---

## O que foi implementado

### 1. Summarizer Agent (Fase 6)

| Artefato | Mudança |
|---|---|
| `pipeline/schemas/summarizer_out.json` | **Novo** — JSON Schema 2020-12 para o output do summarizer |
| `pipeline/prompts/06_summarize.txt` | **Atualizado** — prompt completo com `{pytest_output}` e `{acceptance_criteria}` |
| `pipeline/agents/summarizer.py` | **Implementado** — `run()`, `save_report()`, truncagem de output, `_build_prompt()` |
| `pipeline/workflow/runner.py` | **Atualizado** — `run_phase6()` independente + `PIPELINE_PHASE=phase6` no `main()` |

**Decisões aplicadas a partir da revisão sênior:**
- `run_phase6()` é **independente** de `run_phase5()` — presume que `generated/scripts/` já existe.
  Rodar phase5 antes (LLM calls caras) não é responsabilidade da phase6.
- `selenium_logs` removido da assinatura de `run()` — sem mecanismo real de captura.
  O summarizer recebe `pytest_output: str` + `blob: ContextBlob`.
- `save_report()` usa `Path`, não `str` — consistente com o restante do codebase.
- Truncagem implementada em `_truncate_pytest_output()`: preserva os últimos 8.000 chars
  (pytest coloca falhas no final).
- `subprocess.run` usa `sys.executable` via `[sys.executable, "-m", "pytest", ...]` —
  garante o mesmo interpretador do container.
- Sem dependência de `pytest-json-report` — stdout do pytest com `--tb=short -v` é
  suficiente e legível para o LLM.

---

### 2. Infraestrutura Selenium

| Artefato | Mudança |
|---|---|
| `docker-compose.yml` | Serviço `selenium` descomentado; healthchecks adicionados a `backend`, `frontend`, `selenium`; `depends_on` com `condition: service_healthy` |
| `pipeline/prompts/05_codegen.txt` | Regras 13–14 adicionadas: `webdriver.Remote` + env vars `SELENIUM_REMOTE_URL`/`BASE_URL` |

**Healthchecks adicionados:**
- `backend`: `curl -f http://localhost:8000/docs` (curl está instalado no Dockerfile.backend)
- `frontend`: `wget -qO- http://localhost:5173/` (wget via BusyBox no node:22-alpine)
- `selenium`: `curl -f http://localhost:4444/wd/hub/status` (curl incluso na imagem oficial)

**`VITE_API_BASE_URL` alterado para `http://backend:8000`:**
- **Motivo:** o browser dentro do container `selenium` resolve `localhost` como o próprio
  container selenium, não o backend. Usando o hostname Docker `backend:8000`, o fetch
  da aplicação React chega ao backend via rede interna.
- **Impacto:** acesso via browser no host (`http://localhost:5173`) agora chama
  `http://backend:8000` que **não é resolvível fora do Docker**. Para dev no host:
  ```bash
  VITE_API_BASE_URL=http://localhost:8001 docker compose up frontend
  ```
  Ou adicionar ao `.env` local (não commitado):
  ```
  VITE_API_BASE_URL=http://localhost:8001
  ```

**Prompt 05_codegen.txt:** scripts novos gerados pelo Agent 3 já incluirão `webdriver.Remote`.
Scripts gerados anteriormente (se houver em `generated/`) precisam ser **regenerados** via
`PIPELINE_PHASE=phase5` para usar o novo padrão.

---

### 3. Testes

| Arquivo | Mudança |
|---|---|
| `pipeline/tests/test_summarizer.py` | **Novo** — 5 testes: truncagem, run() válido, run() com schema inválido, save_report(), criação de dirs |
| `pipeline/tests/test_runner.py` | **Atualizado** — 2 novos testes: `run_phase6()` com subprocess mockado, fase6 com scripts ausentes |

---

## Como usar

### Executar a pipeline completa (fases 4+5+6)

```bash
# 1. Subir toda a stack (inclui selenium agora)
docker compose up -d --build

# 2. Gerar casos de teste e scripts (phases 4+5)
docker compose run --rm \
  -e PIPELINE_PHASE=phase5 \
  -e LLM_PROVIDER=gemini \
  -e LLM_MODEL=gemini-2.5-flash \
  pipeline python -m pipeline.workflow.runner

# 3. Aguardar selenium estar healthy
docker compose ps selenium   # Status deve ser "healthy"

# 4. Executar scripts + sumarizar (phase6)
docker compose run --rm \
  -e PIPELINE_PHASE=phase6 \
  -e LLM_PROVIDER=gemini \
  -e LLM_MODEL=gemini-2.5-flash \
  pipeline python -m pipeline.workflow.runner
```

### Rodar apenas os testes unitários do pipeline

```bash
docker compose run --rm pipeline pytest pipeline/tests/ -v
```

### Rodar os scripts Selenium gerados manualmente

```bash
docker compose run --rm pipeline pytest generated/scripts/ --tb=short -v
```

---

## Limitações conhecidas

- **US-03..05 bloqueadas pelo Agent 0** (omissões reais nos critérios) — phase6 só
  processará as histórias cujos scripts existem em `generated/scripts/`.
- **`VITE_API_BASE_URL=http://backend:8000`** quebra o acesso via browser no host.
  Use a variável de ambiente para override em dev local.
- **Scripts existentes** em `generated/` (de runs anteriores ao prompt fix) não usam
  `webdriver.Remote` — regenerar com phase5.
- **`effort_timings.json`** continua com zeros — tempo de análise humana não medido.
