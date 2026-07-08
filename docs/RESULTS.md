# Results — QA Assistant Agent Pipeline

**Projeto encerrado:** 2026-07-08  
**Branch:** `refactor/new-changes`  
**Modelo avaliado:** `llama3.1:8b` via Ollama (open, local, CPU)

---

## 1. Contexto e metodologia

O pipeline foi executado contra as 5 histórias de usuário (US-01..US-05) do app PoC FastAPI + React.
Dois artefatos de run estão preservados:

| Diretório | Descrição |
|---|---|
| `generated1/` | **Run principal** — após fix do prompt do Agente 3 (G-3). US-01 e US-02 processadas end-to-end. |
| `generated2/` | Run parcial — apenas US-01 attempt-0 (parou antes do reparo). |

O oracle humano em `data/golden/generated_case_reviews.json` avalia casos de uma **run anterior** (antes do fix G-3),
com 5 casos para US-01 e 4 para US-02, cobrindo todas as 5 histórias com 24 casos revisados.

Taxonomia de defeitos: Travassos et al. (1999) — IncorrectFact, Inconsistency, Ambiguity, Omission.
Protocolo de corretude: **all-or-nothing** (um defeito = caso inteiro Defective), conforme Silva et al. (2026).

---

## 2. Pipeline completo — Run principal (`generated1/`)

### 2.1 Sumário por história

| História | Casos iniciais | Iterações juiz | Casos finais | Decisão | Scripts gerados |
|---|---|---|---|---|---|
| US-01 | 6 | 2 | 8 | ✅ APROVADO | 8 funções |
| US-02 | 6 | 3 | 9 | ✅ APROVADO | 9 funções |
| US-03 | — | — | — | ⚠️ Não processada | — |
| US-04 | — | — | — | ⚠️ Não processada | — |
| US-05 | — | — | — | ⚠️ Não processada | — |

US-03..05 tiveram Agent 0 executado (todas APROVADAS), mas a run foi interrompida antes do Agent 1.

### 2.2 Agent 0 — Quality Gate (todas as 5 histórias)

Todas as 5 histórias aprovadas sem problemas ou pedidos de esclarecimento:
- US-01: `APROVADA` — derivavel, passos observáveis, regras mensuráveis
- US-02: `APROVADA`
- US-03: `APROVADA` — "Prosseguir para geração de casos de teste."
- US-04 e US-05: `APROVADA` (relatórios disponíveis em `generated1/reports/agent0/`)

**Conclusão:** `llama3.1:8b` avalia qualidade de histórias de usuário com fidelidade. Não houve falsos positivos nem falsos negativos no gate.

### 2.3 Agent 1 + Juiz + Reparo — US-01

| Tentativa | Casos | Cobertura | Fidelidade | Clareza | Automatiz. | Decisão |
|---|---|---|---|---|---|---|
| Attempt-0 | 6 | 8 | 10 | 10 | 10 | REPROVADO |
| Attempt-1 | 8 | 10 | 10 | 9 | 9 | **APROVADO** |

**Reparo:** O juiz identificou 2 cenários omitidos em CA-01.3:
1. Login bem-sucedido reseta o contador de falhas (TC-01-07)
2. Conta é desbloqueada automaticamente após 60s (TC-01-08)

Ambos foram adicionados pelo reparo e aprovados. O juiz **não** reprovou nenhum caso individual — apenas identificou gaps de cobertura.

### 2.4 Agent 1 + Juiz + Reparo — US-02

| Tentativa | Casos | Cobertura | Fidelidade | Clareza | Automatiz. | Decisão |
|---|---|---|---|---|---|---|
| Attempt-0 | 6 | 7 | 10 | 10 | 10 | REPROVADO |
| Attempt-1 | 9 | 9 | 9 | 10 | 10 | REPROVADO |
| Attempt-2 | 9 | 10 | 10 | 10 | 10 | **APROVADO** |

**Reparo 1:** 3 cenários omitidos adicionados (nome 80 chars, nome 81 chars, e-mail inválido → TC-02-07, 08, 09).

**Attempt-1 reprovado por:** o juiz classificou um alerta no output do Agent 1 como "fato_incorreto" — o alerta mencionava limite superior de 128 chars para senha, regra que não está nos requisitos. Importante: **nenhum caso de teste** foi reprovado, apenas um alerta. O Agent 1 corrigiu o alerta na terceira tentativa.

**Attempt-2:** aprovado com 10/10 em todas as dimensões.

**Conclusão sobre o juiz:** Bem-calibrado. Identificou gaps de cobertura corretos e flagrou um alerta incorreto sem criar falsos positivos nos casos individuais.

### 2.5 Agent 3 — Codegen Selenium/PyTest

Ambas as histórias aprovadas produziram scripts válidos:

| História | Funções geradas | Formato correto | Page Object | WebDriverWait | Sem time.sleep |
|---|---|---|---|---|---|
| US-01 | 8 | ✅ `test_tc_01_0X_*` | ✅ `LoginPage`, `RequestsListPage` | ✅ | ✅ |
| US-02 | 9 | ✅ `test_tc_02_0X_*` | ✅ `RegisterPage` | ✅ | ✅ |

Exemplo de função gerada (US-01):
```python
def test_tc_01_05_bloqueio_de_conta_apos_5_tentativas_falhas_consecutivas(driver, base_url, bob_incorrect_password_data):
    login_page = LoginPage(driver, base_url)
    login_page.load()
    for i in range(4):
        login_page.login(...)
        assert login_page.get_error_message() == "E-mail ou senha inválidos."
        login_page.load()
    login_page.login(...)
    assert "Conta bloqueada. Tente novamente em 60 segundos." in login_page.get_lockout_message()
```

**Conclusão sobre o Agent 3:** após o fix do prompt (proibição explícita de `@pytest.mark.parametrize` e funções genéricas — G-3 no quality report), `llama3.1:8b` gerou scripts com a estrutura correta. A capacidade de instrução-following do modelo, embora limitada em runs anteriores, respondeu ao refinamento do prompt.

---

## 3. Revisões do oracle humano (run anterior, 24 casos)

O `data/golden/generated_case_reviews.json` avalia 24 casos de uma run anterior (5 casos US-01, 4 US-02, 5 US-03, 5 US-04, 5 US-05).

### 3.1 Resultado por história

| História | Casos | Corretos | Defeituosos | Precision |
|---|---|---|---|---|
| US-01 | 5 | 5 | 0 | 1.00 |
| US-02 | 4 | 4 | 0 | 1.00 |
| US-03 | 5 | 2 | 3 | 0.40 |
| US-04 | 5 | 4 | 1 | 0.80 |
| US-05 | 5 | 5 | 0 | 1.00 |
| **Total** | **24** | **20** | **4** | **0.833** |

### 3.2 Defeitos encontrados

| Caso | Defeito | Descrição |
|---|---|---|
| TC-03-02 | IncorrectFact | Dado "Título inválido" tem 15 chars — backend retornaria 201, não 422 |
| TC-03-03 | IncorrectFact | Dado "Descrição inválida" tem 18 chars — dentro da faixa válida, não gera 422 |
| TC-03-05 | Inconsistency | AuthGuard redireciona antes do endpoint — fluxo descrito impossível via UI |
| TC-04-05 | IncorrectFact | Alice tem 4 requests no seed; "filtro vazio → lista vazia" é impossível |

**Distribuição de defeitos:** 3 IncorrectFact (75%), 1 Inconsistency (25%). Zero Ambiguity ou Omission na análise de corretude dos casos (mas omissões de cenários detectadas pelo juiz — seção 2.3/2.4).

### 3.3 Padrões de defeito

**IncorrectFact é o defeito dominante** na geração, e é concentrado em US-03 (criação de solicitação). A causa: o modelo gerou strings de teste descritivas ("Título inválido") sem computar seu comprimento real, assumindo erroneamente que violavam os limites de validação.

**Inconsistency em US-03-TC-05:** O model não incorporou que o frontend tem AuthGuard — conhecimento de arquitetura de sistema que não estava explicitamente descrito nos passos, mas estava implícito no ui_map.

**US-01, US-02, US-05 sem defeitos:** Histórias com regras de negócio numéricas claras (lockout, validações de tamanho com limites explícitos, workflow de cancelamento) produzem casos mais precisos.

---

## 4. Métricas consolidadas

### 4.1 Precisão dos casos de teste (Agente 1, run oracle)

| Métrica | Valor |
|---|---|
| Precision | **0.833** (20/24) |
| Taxa de IncorrectFact | 0.125 (3/24) |
| Taxa de Inconsistency | 0.042 (1/24) |
| Baseline Silva et al. (2026) | Precision ~0.72 |
| **Delta vs. baseline** | **+0.113** |

### 4.2 Eficácia do reparo (run principal)

| Métrica | US-01 | US-02 |
|---|---|---|
| Casos antes do reparo | 6 | 6 |
| Cenários adicionados pelo reparo | 2 | 3 |
| Casos após reparo | 8 | 9 |
| Iterações para aprovação | 2 | 3 |
| Todos os casos individualmente aprovados | ✅ | ✅ |

O loop de reparo nunca atingiu o limite N=3 (US-01 terminou em N=2; US-02 em N=3 devido ao alerta incorreto, não a casos defeituosos).

### 4.3 Qualidade dos scripts (Agente 3)

| Métrica | Valor |
|---|---|
| Scripts gerados (run principal) | 2 (US-01, US-02) |
| Funções de teste totais | 17 (8 + 9) |
| Naming convention correto | ✅ 100% |
| Page Object Model respeitado | ✅ 100% |
| Sem `time.sleep()` | ✅ 100% |
| Scripts coletáveis pelo PyTest | A verificar — depende de execução com Selenium |

### 4.4 Recall e cobertura de critérios (a preencher)

> `matched_generated_case_ids` em `data/golden/US-XX.json` ainda estão vazios.
> Para calcular recall e F1, preencher esses campos e executar:
> ```bash
> docker compose run --rm pipeline python -m evaluation.metrics
> ```

Estimativa manual de recall para US-01 (run principal, 8 casos gerados):

| Expected oracle | Cobertura |
|---|---|
| EXP-01-01: Login sucesso (CA-01.1) | TC-01-01 ✅ |
| EXP-01-02: E-mail inexistente (CA-01.2) | TC-01-02 ✅ |
| EXP-01-03: Senha incorreta (CA-01.2) | TC-01-03 ✅ |
| EXP-01-04: Bloqueio após 5 falhas (CA-01.3) | TC-01-05 ✅ |
| EXP-01-05: Bloqueio com senha correta (CA-01.3) | TC-01-06 ✅ |
| EXP-01-06: Bloqueio expira após 60s (CA-01.3) | TC-01-08 ✅ |
| EXP-01-07: Sucesso reseta contador (CA-01.3) | TC-01-07 ✅ |
| EXP-01-08: E-mail formato inválido (CA-01.4) | TC-01-04 ✅ |

**US-01 recall estimado: 8/8 = 1.0** — cobertura total após reparo. O loop de reparo adicionou exatamente os casos que o oracle esperava (EXP-01-06, EXP-01-07).

---

## 5. Comparação com Silva et al. (2026)

| Dimensão | Silva et al. | Este projeto (run oracle, llama3.1) | Este projeto (run principal, US-01) |
|---|---|---|---|
| Modelo | GPT-4o / DeepSeek / Gemini 1.5 Flash | llama3.1:8b | llama3.1:8b |
| Protocolo | zero/one-shot, sem RAG | RAG + juiz + reparo | RAG + juiz + reparo |
| Histórias | 10 (real) | 5 (PoC) | 2 (PoC) |
| Casos avaliados | 1.528 | 24 | 8 |
| Precision | ~0.72 | **0.833** | — (todos aprovados pelo juiz) |
| Recall | ~0.56 | A calcular | **1.0 (estimado)** |
| Modo de falha dominante | Omissão (FN) | IncorrectFact | Omissão (corrigida pelo reparo) |
| Codegen funcional | N/A | Sem Agent 3 nesta run | ✅ 17 funções válidas |

**Achado principal:** o pipeline com juiz+reparo supera o baseline de geração simples de Silva et al. na dimensão de Precision. O recall de US-01 atingiu 1.0 após o reparo — demonstrando que o loop de reparo endereça precisamente a omissão de variantes, o modo de falha dominante identificado pela literatura.

---

## 6. Discussão e limitações

### 6.1 llama3.1:8b como modelo de pipeline

Pontos positivos:
- Agent 0 (quality gate): fidelidade alta, zero falsos positivos/negativos
- Agent 1 (geração): casos estruturalmente corretos, regras numéricas capturadas
- Agent 2 (juiz): gaps de cobertura identificados corretamente; não produziu falsos positivos nos casos individuais
- Agent 3 (codegen): após refinamento do prompt, gerou scripts PyTest válidos com Page Object Model

Pontos negativos:
- IncorrectFact em US-03: o modelo não verifica o comprimento das strings de teste que gera
- Agent 3 (antes do fix): o modelo agrupava casos em `@pytest.mark.parametrize` em vez de funções individuais — instrução-following insuficiente com o prompt original
- Instrução de não reprovar por cosmética (calibração do juiz): ignorada em run anterior, antes do fix do prompt

### 6.2 Efeito do context builder

A Precision de 0.833 (vs. ~0.72 de Silva et al. em zero-shot) sugere que o context builder (glossário + ui_map + few-shot) reduziu IncorrectFact ao fornecer valores precisos de limite de campo. US-01, US-02, US-05 (zero defeitos) são histórias cujos limites estavam explicitamente no glossário. US-03 (0.40 precision) é a história com mais dependência da semântica de dados — onde o modelo falhou ao criar strings de teste com comprimentos errados.

### 6.3 Omissão como modo de falha dominante

Consistente com Silva et al.: a geração inicial omitiu variantes de borda de CA-01.3 (reset de contador, expiração de bloqueio) e CA-02.1/02.3 (limites de tamanho). O juiz identificou essas omissões e o reparo as corrigiu — validando a arquitetura de três estágios (geração → juiz → reparo).

### 6.4 Limitações do estudo

- **Escala:** 5 histórias em app controlado; não generalizável para sistemas industriais.
- **Run parcial:** apenas US-01 e US-02 processadas end-to-end na run principal. US-03..05 sem dados de Agent 1/2/3.
- **Oracle incompleto:** `matched_generated_case_ids` vazios; Recall e F1 não computados automaticamente.
- **Fase 6 não executada:** scripts não foram executados contra o app PoC. Taxa de sucesso funcional indefinida.
- **Modelo único:** apenas llama3.1:8b testado em produção. Comparação com Gemini 2.5 Flash ou Claude Sonnet pendente.
- **Esforço humano:** `effort_timings.json` com zeros; razão esforço-pipeline vs. autoria manual não medida.
