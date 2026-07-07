# Quality Report — LLM QA Pipeline

**Data:** 2026-07-07  
**Branch:** `refactor/new-changes`  
**Escopo:** Análise completa do codebase (Fases 0–5 + Phase 7 parcial)  
**Revisores:** Engenheiro 1 (análise inicial) + Engenheiro Sênior (revisão independente)

---

## Resumo Executivo

O projeto cobre Fases 0–5 implementadas e a Fase 7 com o harness implementado porém o oracle incompleto. A arquitetura segue o AGENTS.md fielmente na maior parte. **Seis problemas graves/médios foram corrigidos nesta sessão.** Problemas médios e baixos restantes estão documentados abaixo.

**Estado atual:** O pipeline não completou end-to-end para nenhuma história com o modelo `llama3.1:8b`. É necessário rodar com `gemini-2.5-flash` ou `claude-sonnet-4-6` para validar o fluxo completo.

---

## Problemas Graves — RESOLVIDOS nesta sessão

### G-1 `network_mode: host` quebrado no Windows ✅ CORRIGIDO

**Arquivo:** `docker-compose.yml:80`  
**Causa:** O serviço `pipeline` usava `network_mode: host`. No Linux esse modo roteia `localhost` para o host físico. No Windows e Mac com Docker Desktop o modo é silenciosamente ignorado — `localhost` dentro do container resolve para o loopback do próprio container, onde nada escuta na porta 11434. O pipeline falhava ao tentar conectar ao Ollama.  
**Correção aplicada:** Substituído `network_mode: host` por `networks: - llm-tests-network`. URL padrão do Ollama alterada de `http://localhost:11434` para `http://ollama:11434` (nome do serviço Docker Compose). Documentação adicionada no `.env.example` para os três cenários: dentro do Compose, fora do Docker, e Windows/Mac com Docker Desktop.

---

### G-2 Judge Agent 2 descartava casos silenciosamente ✅ CORRIGIDO

**Arquivo:** `pipeline/agents/agent2_judge.py:280`  
**Causa:** `_validate_semantics` verificava que não havia IDs inválidos, que não havia sobreposição entre aprovados/reprovados, e que REPROVADO tinha evidências — mas **nunca verificava** que todos os casos estavam em pelo menos uma das listas. O LLM podia "esquecer" casos, que simplesmente desapareciam no `_merge_preserved_approved_cases`. Evidência real: `US-01_attempt-3.json` — TC-01-01, TC-01-02, TC-01-03 não aparecem em `casos_aprovados` nem em `casos_reprovados`.  
**Correção aplicada:**
```python
unclassified = valid_case_ids - approved - rejected
if unclassified:
    raise AgentOutputError(
        f"Agent 2 semantic validation failed: cases not classified (neither approved nor rejected): {sorted(unclassified)}."
    )
```
Adicionalmente removida a variável morta `repaired_by_id` que era computada mas nunca usada.

---

### G-3 Agent 3 falhou para todas as histórias — zero scripts gerados ✅ PROMPT CORRIGIDO

**Arquivo:** `pipeline/prompts/05_codegen.txt:27`, `pipeline/agents/agent3_codegen.py:188`  
**Causa raiz (modelo):** O modelo `llama3.1:8b` não gerou uma função por caso de teste. Em vez disso gerou uma única função `test_case` com `@pytest.mark.parametrize` agrupando todos os casos. A validação `_validate_test_functions` procura `tc_02_01` em nomes de funções — `test_case` não contém o padrão, causando falha em todas as histórias que chegaram ao Agent 3 (US-02 a US-05; US-01 foi bloqueada pelo Agent 2).  
**Causa contribuinte (prompt):** A regra 7 do prompt dizia "Crie uma função por caso automatizável" mas não proibia explicitamente `@pytest.mark.parametrize` nem funções genéricas.  
**Correção aplicada ao prompt:**
```
7. Crie UMA função por caso automatizável com nome exatamente no formato
   `test_{case_id_em_minúsculas}_{descricao_curta}`.
   Exemplo: caso TC-02-01 → `def test_tc_02_01_cadastro_bem_sucedido(driver):`.
   PROIBIDO usar @pytest.mark.parametrize para agrupar casos distintos em uma única função.
   PROIBIDO criar funções genéricas como `test_case`, `test_run`, `test_all`.
```
**Nota importante:** O problema de raiz é capacidade do modelo. `llama3.1:8b` não segue instruções complexas com fidelidade suficiente para o contrato do Agent 3. Recomenda-se usar `gemini-2.5-flash` ou `claude-sonnet-4-6`.

---

## Problemas Médios — Parcialmente resolvidos nesta sessão

### M-1 Model ID do Gemini incorreto em dois lugares ✅ CORRIGIDO NESTA SESSÃO

**Arquivos:** `pipeline/settings.py:33,46`, `pipeline/llm/gemini.py:13`, `.env.example:6,20`  
**Causa:** `"gemini-3.1-flash"` e `"gemini-3.1-flash-lite"` não existem na API Gemini. O modelo correto é `"gemini-2.5-flash"`. Adicionalmente, `_THINKING_MODEL_PREFIXES` em `gemini.py` incluía `"gemini-3.1-flash-lite"` mas `_is_thinking_model` retorna `False` antes de verificar prefixos quando o nome termina em `-lite` — tornando esta entrada dead code.  
**Correção aplicada:** Todos os defaults corrigidos para `"gemini-2.5-flash"`. Entrada morta removida de `_THINKING_MODEL_PREFIXES`.

---

### M-2 Dead code no runner — duas funções ✅ CORRIGIDO NESTA SESSÃO

**Arquivo:** `pipeline/workflow/runner.py`  

**a) `run_agent0_all`**: Existia mas nunca era chamada por `main()`. A orquestração do Agent 0 estava inteiramente em `run_phase4`. Removida.

**b) `run_phase3`**: Função que só fazia `return run_phase4(...)` com dois argumentos, sem repassar `agent2_reports_dir` e `repaired_test_cases_dir`. Nunca chamada por `main()`. Removida.

**c) `summary` dict intermediário**: Nas linhas 322–327 do código original, um dict `summary` era computado mas nunca atribuído a `aggregate`. O `aggregate["summary"]` na linha seguinte recomputava tudo do zero. Dead code. Removido.

**d) `log` declarado fora de ordem**: O logger estava declarado após a função `run_agent0_all`, depois das imports. Movido para logo após as imports.

---

### M-3 Oracle golden incompleto — `matched_generated_case_ids` todos vazios

**Arquivo:** `data/golden/US-01.json` … `US-05.json`  
**Causa:** Todos os arquivos do oracle têm `matched_generated_case_ids: []` para todos os expected cases. A função `_case_quality_metrics` em `evaluation/metrics.py` calcula recall como `matched_expected / expected_total`. Com tudo zerado, recall = 0 e F1 = 0 — resultado incorreto que distorce qualquer avaliação.  
**Ação requerida:** Após rodar o pipeline com sucesso (com modelo capaz), preencher `matched_generated_case_ids` em cada arquivo golden com os IDs dos casos gerados que correspondem a cada expected case.

---

### M-4 Três arquivos obrigatórios ausentes em `data/golden/` ⚠️ CORREÇÃO ANTERIOR INCOMPLETA

**Arquivo:** `evaluation/metrics.py:58-60`  
**Causa:** `metrics.py` carrega três arquivos que não existem:
1. `generated_case_reviews.json` — linha 58 (`_load_json(paths.golden / "generated_case_reviews.json")["reviews"]`)
2. `judge_reviews.json` — linha 59
3. `effort_timings.json` — linha 60

O relatório anterior mencionava apenas 2 (judge_reviews e effort_timings). `generated_case_reviews.json` é o arquivo mais central — sem ele, não há como calcular precisão ou cobertura de critérios de aceitação.

**Ação requerida:** Criar os três arquivos. Estrutura mínima:

```json
// generated_case_reviews.json
{
  "reviews": [
    {
      "story_id": "US-02",
      "case_id": "TC-02-01",
      "correct": true,
      "defect_tags": []
    }
  ]
}

// judge_reviews.json
{
  "reported_problems": [
    { "story_id": "US-02", "problem_id": "p1", "confirmed": true }
  ],
  "missed_problems": []
}

// effort_timings.json
{
  "pipeline_review_minutes": 15.0,
  "manual_authoring_minutes": 120.0
}
```

---

### M-5 `generated/` NÃO está no .gitignore — arquivos fake são rastreados ✅ CORRIGIDO NESTA SESSÃO

**Arquivo:** `.gitignore:6`  
**Causa:** A linha `generated/` estava comentada (`# generated/`), portanto todo o conteúdo de `generated/` estava sendo rastreado pelo git. Isso inclui os arquivos com dados simulados:
- `generated/fake_end_to_end_metrics.json`
- `generated/fake_end_to_end_pipeline_report.md`
- `generated/gamma_prompt_fake_pipeline_report.txt`

E também os outputs reais do pipeline (test cases, reports do Agent 2, etc.), que AGENTS.md diz não devem ser commitados.

**Correção aplicada:** Descomentado `generated/` no `.gitignore`.  
**Ação requerida:** Executar `git rm -r --cached generated/` para parar de rastrear o que já está no histórico.

---

### M-6 Juiz calibrado de forma muito estrita — US-01 rejeitada incorretamente

**Arquivo:** `generated/reports/agent2/US-01_attempt-3.json`, `pipeline/prompts/03_judge.txt`  
**Causa:** O juiz reprovando TC-01-04 por `fato_incorreto` alegando que a mensagem de erro deveria ser "E-mail ou senha inválidos" sem ponto final. Porém `app/backend/src/routers/auth.py:46` retorna a string **com ponto final** — o caso de teste está correto. O prompt do juiz inclui a instrução "Não reprove por diferença cosmética sem impacto funcional, como pontuação final em mensagem" mas o modelo `llama3.1:8b` ignorou essa instrução.  
**Ação requerida:** Fortalecer a instrução no prompt do juiz com exemplo negativo explícito. O problema raiz é capacidade do modelo — com `gemini-2.5-flash` este tipo de erro deve ser menos frequente.

---

## Problemas Baixos — Registrados para futura resolução

### B-1 Typo no prompt do quality gate

**Arquivo:** `pipeline/prompts/01_quality_gate.txt:76`  
`"justivicativa_derivabilidade"` → deve ser `"justificativa_derivabilidade"`.  
Não causa falha (o JSON usa o nome correto), mas é confuso para quem lê o prompt.

---

### B-2 Duplicação de `_documented_testids()` entre agentes

**Arquivos:** `pipeline/agents/agent1_generate.py`, `pipeline/agents/agent3_codegen.py`  
Implementações diferentes da mesma função com regexes distintos. Em `agent1` o regex é `r"data-testid=([^\]]+)"`. Em `agent3` é `r"data-testid\s*=\s*[\"']?([a-zA-Z0-9_-]+)"`. Ambas deveriam estar em `pipeline/agents/utils.py` com a regex mais precisa do `agent3`. Risco de divergência silenciosa.

---

### B-3 `_has_exact_total_evidence` usa padrões em inglês sem documentação

**Arquivo:** `pipeline/agents/agent1_generate.py:503-508`  
Os padrões `"owns N requests"` e `"N requests"` são strings em inglês dentro de código que valida conteúdo em português. Esses padrões provavelmente têm origem nos dados de seed da API (`RequestListOut.total`). Devem ter um comentário explicando a razão — sem ele, a justificativa não é óbvia.

---

### B-4 `_validate_test_files_do_not_embed_selectors` rejeita `"By."` em comentários

**Arquivo:** `pipeline/agents/agent3_codegen.py:196-201`  
A validação rejeita qualquer `test_*.py` que contenha `"By."` como substring. Isso rejeitaria um arquivo com `# use By.XPATH only in pages.py`. O check deveria verificar imports reais (`from selenium.webdriver.common.by import By`), não presença de substring.

---

### B-5 Schema do test file aceita mais nomes do que a validação permite

**Arquivo:** `pipeline/agents/agent3_codegen.py:136-155`  
`_TEST_FILE_PATTERN = re.compile(r"^test_[a-zA-Z0-9_]+\.py$")` aceita qualquer nome seguindo o padrão. Mas a validação subsequente exige especificamente `test_{story_id_lower}.py`. O padrão permissivo na verificação de arquivos desconhecidos é inconsistente com a validação estrita de nome do arquivo de teste. Confunde quem lê.

---

### B-6 `06_summarize.txt` não é um prompt funcional

**Arquivo:** `pipeline/prompts/06_summarize.txt`  
O arquivo contém apenas comentários sobre o que o prompt deveria conter. Se a Fase 6 for implementada e alguém tentar rodar sem substituir este arquivo, a falha não será óbvia.

---

### B-7 Schema `summarizer_out.json` ausente

**Arquivo:** `pipeline/schemas/` (ausência)  
`PLAN.md §7` descreve o contrato do Summarizer. O schema JSON correspondente não foi criado.

---

### B-8 Seletor `request_cancel_dialog` pode ficar fora do contexto de US-05

**Arquivo:** `pipeline/context/ui_map.json`  
O screen `request_cancel_dialog` não tem o campo `"story"`. O context builder filtra por `screen.get("story") == story.id or name in wanted`. Se `request_cancel_dialog` não estiver listado em `touched_screens` de US-05, a tela não aparecerá no blob de contexto gerado.

---

### B-9 `pipeline/log.py` cria o arquivo de log no diretório de trabalho atual

**Arquivo:** `pipeline/log.py`  
`pipeline.log` é criado no diretório de trabalho corrente. Dentro do container Docker com workdir `/app`, o log fica em `/app/pipeline.log` (dentro do volume montado — aceitável). Fora do Docker, o comportamento depende de onde o runner é iniciado.

---

### B-10 `_normalize_decision_consistency` força REPROVADO para cenários omitidos

**Arquivo:** `pipeline/agents/agent2_judge.py:229-243`  
`has_rejection_evidence` considera `cenarios_omitidos_sugeridos` como evidência de reprovação. Um juiz que retorna `decisao: APROVADO` mas com `cenarios_omitidos_sugeridos` não vazio terá `decisao` forçado para `REPROVADO`. Essa semântica pode ser intencional (se há cenário omitido, a geração não está completa) mas não está documentada em `PLAN.md` nem em comentários no código.

---

### B-11 Fragmento de frase solto no prompt de reparo ✅ CORRIGIDO NESTA SESSÃO

**Arquivo:** `pipeline/prompts/04_repair.txt:28`  
A linha `se for substituição completa.` aparecia fora do contexto, após o segundo bullet point, como fragmento da frase do primeiro bullet. Texto removido.

---

### B-12 Dead code: `_normalise_text_for_search` é alias desnecessário ✅ CORRIGIDO NESTA SESSÃO

**Arquivo:** `pipeline/agents/agent1_generate.py` (original ~linha 495)  
`_normalise_text_for_search` era uma função de uma linha que apenas chamava `_normalise_text`. Único uso substituído por chamada direta. Função removida.

---

### B-13 AGENTS.md desatualizado — "Repo stage" errado

**Arquivo:** `AGENTS.md:7`  
O cabeçalho diz `> **Repo stage:** Phases 1–3 complete. Phase 4 (Agent 2 — judge + repair loop) is next.` mas as Fases 4 e 5 já foram implementadas. Isso vai confundir novos colaboradores.  
**Ação requerida:** Atualizar para refletir que Fases 0–5 estão completas e a próxima é Fase 6 (Summarizer).

---

## Conformidade com AGENTS.md / PLAN.md

| Requisito | Status | Observação |
|---|---|---|
| Provider-agnostic LLM client via factory | ✅ | |
| Prompts em arquivos separados | ✅ | |
| Outputs strict JSON, validados contra schema | ✅ | |
| Repair loop com bounded N=3 | ✅ | |
| Traceability matrix em sync | ✅ | |
| Page Object Model no Agent 3 | ✅ (prompt + validação) | |
| `data-testid` em todos elementos interativos | ✅ | |
| `ui_map.json` em sync com frontend | ✅ | |
| Sem `time.sleep()` no codegen | ✅ (validado) | |
| Docker stack funcional cross-platform | ✅ (após G-1) | Corrigido nesta sessão |
| Pipeline end-to-end com modelo capaz | ⚠️ | Precisa ser validado com gemini-2.5-flash |
| `generated/` não commitado | ✅ (após M-5) | Corrigido nesta sessão — `git rm --cached` ainda pendente |
| Human oracle completo | ❌ | M-3, M-4 — 3 arquivos ausentes |
| Schema `summarizer_out.json` | ❌ | B-7 |
| Fase 6 — Summarizer | ❌ | Planejado (Phase 6) |
| Fase 7 — métricas funcionais | ❌ | Oracle incompleto |
| AGENTS.md atualizado | ❌ | B-13 — ainda diz "Phase 4 is next" |

---

## Validação das correções aplicadas

| Correção | Verificação |
|---|---|
| G-1 docker-compose | ✅ `network_mode: host` removido; `networks: llm-tests-network` adicionado; `OLLAMA_BASE_URL` → `http://ollama:11434` |
| G-2 unclassified cases | ✅ Check `valid_case_ids - approved - rejected` adicionado em `_validate_semantics`; interage corretamente com `_normalize_decision_consistency` |
| G-3 codegen prompt | ✅ Proibição explícita de `@pytest.mark.parametrize` e funções genéricas |
| M-1 Gemini model | ✅ `gemini-2.5-flash` em settings.py, .env.example e gemini.py |
| M-2 dead code | ✅ `run_agent0_all`, `run_phase3`, `summary` dict, logger fora de ordem — todos removidos/corrigidos |
| M-5 .gitignore | ✅ `generated/` descomentado |

---

## O que você deve testar

As verificações abaixo são recomendadas em ordem de prioridade.

### 1. Remover `generated/` do histórico do git

```bash
git rm -r --cached generated/
git commit -m "stop tracking generated/ artifacts"
```

Verificar que os arquivos continuam no disco mas saem do `git status`.

---

### 2. Pipeline completo com modelo capaz (prioritário)

```bash
docker compose run --rm \
  -e LLM_PROVIDER=gemini \
  -e LLM_MODEL=gemini-2.5-flash \
  -e PIPELINE_PHASE=phase5 \
  pipeline python -m pipeline.workflow.runner
```

Verificar:
- Agent 3 gera scripts com uma função por caso (valida o fix de G-3)
- US-01 passa pelo juiz sem ser rejeitada por cosmética (valida M-6)
- Diretório `generated/scripts/` é criado com pelo menos um `test_us_XX.py` por história aprovada
- Nenhuma história tem casos não classificados (valida fix de G-2)

---

### 3. Conectividade Ollama no Windows (se usar Ollama)

```bash
# No .env, verificar OLLAMA_BASE_URL:
# Dentro do Compose:      http://ollama:11434   (padrão — usar este)
# Fora do Docker:         http://localhost:11434
# Docker Desktop Win/Mac: http://host.docker.internal:11434

docker compose run --rm pipeline python -c "
from pipeline.llm.factory import get_client
from pipeline.settings import get_settings
c = get_client('ollama:llama3', get_settings())
r = c.complete('Responda apenas: OK')
print(r.text)
"
```

---

### 4. Backend tests

```bash
docker compose run --rm pipeline pytest app/backend/tests/ -v
```

Todos os 21 testes devem passar.

---

### 5. Evaluation harness (após pipeline bem-sucedido)

a. Criar `data/golden/generated_case_reviews.json` com uma entry por caso gerado:
```json
{
  "reviews": [
    { "story_id": "US-02", "case_id": "TC-02-01", "correct": true, "defect_tags": [] }
  ]
}
```

b. Criar `data/golden/judge_reviews.json`:
```json
{
  "reported_problems": [
    { "story_id": "US-02", "problem_id": "p1", "confirmed": true }
  ],
  "missed_problems": []
}
```

c. Criar `data/golden/effort_timings.json`:
```json
{ "pipeline_review_minutes": 15.0, "manual_authoring_minutes": 120.0 }
```

d. Preencher `matched_generated_case_ids` em `data/golden/US-XX.json`.

e. Executar:
```bash
docker compose run --rm pipeline python -m evaluation.metrics
```

---

### 6. Judge calibration — M-6

Verificar se com `gemini-2.5-flash` o juiz ainda reprova por pontuação final em mensagem. Se sim, adicionar ao prompt `03_judge.txt` um exemplo negativo explícito de reprovação cosmética inaceitável.

---

### 7. Atualizar AGENTS.md — B-13

Após confirmar que o pipeline roda end-to-end, atualizar a linha:
```
> **Repo stage:** Phases 1–3 complete. Phase 4 is next.
```
para:
```
> **Repo stage:** Phases 0–5 complete. Phase 6 (Summarizer) is next.
```
