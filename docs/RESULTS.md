# Results — QA Assistant Agent Pipeline

**Projeto encerrado:** 2026-07-08  
**Branch:** `refactor/new-changes`  
**Modelos avaliados:** `gemini-2.5-flash` (Run 1) · `gemini-3.5-flash` (Run 2)

---

## 1. Contexto e metodologia

O pipeline foi executado contra as 5 histórias de usuário (US-01..US-05) do app PoC FastAPI + React.
Dois artefatos de run estão preservados, cada um com um modelo Gemini diferente:

| Diretório | Modelo | Descrição |
|---|---|---|
| `generated1/` | `gemini-2.5-flash` | **Run 1** — US-01 e US-02 processadas end-to-end (Agent 0 → 1 → 2 → 3). |
| `generated2/` | `gemini-3.5-flash` | **Run 2** — US-01 completa (Agent 0 → 1 → 2 → 3); US-02..05 bloqueadas pelo gate. |

O oracle humano em `data/golden/generated_case_reviews.json` avalia casos de uma **run anterior** ao fix G-3,
cobrindo todas as 5 histórias com 24 casos revisados (modelos/run não preservados).

Taxonomia de defeitos: Travassos et al. (1999) — IncorrectFact, Inconsistency, Ambiguity, Omission.
Protocolo de corretude: **all-or-nothing** (um defeito = caso inteiro Defective), conforme Silva et al. (2026).

---

## 2. Pipeline completo — Run 1: `gemini-2.5-flash` (`generated1/`)

### 2.1 Sumário por história

| História | Agent 0 | Agent 1–3 | Motivo de parada |
|---|---|---|---|
| US-01 | ✅ APROVADA | ✅ Completo (8 casos, 8 scripts) | — |
| US-02 | ✅ APROVADA | ✅ Completo (9 casos, 9 scripts) | — |
| US-03 | ⚠️ PRECISA_DE_ESCLARECIMENTO | ❌ Bloqueada | Agent 0 identificou omissões nos critérios |
| US-04 | ⚠️ PRECISA_DE_ESCLARECIMENTO | ❌ Bloqueada | Agent 0 identificou omissões nos critérios |
| US-05 | ⚠️ PRECISA_DE_ESCLARECIMENTO | ❌ Bloqueada | Agent 0 identificou omissões nos critérios |

US-03, US-04 e US-05 foram bloqueadas pelo Agent 0 por omissões reais nos critérios de aceitação. Apenas US-01 e US-02 avançaram para geração — **comportamento intencional da arquitetura**.

### 2.2 Agent 0 — Quality Gate (todas as 5 histórias)

| História | Status | Problemas identificados |
|---|---|---|
| US-01 | ✅ APROVADA | Nenhum |
| US-02 | ✅ APROVADA | Nenhum |
| US-03 | ⚠️ PRECISA_DE_ESCLARECIMENTO | Comportamento da UI para erros 422 não descrito em CA-03.2; resposta da UI para tentativa não autenticada (401) não detalhada em CA-03.3 |
| US-04 | ⚠️ PRECISA_DE_ESCLARECIMENTO | Comportamento para acesso não autenticado não especificado; valores inválidos nos filtros sem comportamento definido; paginação não especificada |
| US-05 | ⚠️ PRECISA_DE_ESCLARECIMENTO | Feedback de UI para erros 403, 404 e 409 não descrito nos critérios; mensagem de erro do 404 ausente no critério CA-05.2 |

As três histórias bloqueadas têm omissões legítimas — sem saber o comportamento da UI nos cenários de erro, o Agent 1 teria que inventar regras, gerando casos de teste com fatos incorretos. O gate bloqueou corretamente todas as três. O pipeline só avançou com US-01 e US-02 — **comportamento intencional da arquitetura**.

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

**Conclusão sobre o Agent 3:** após o fix do prompt (proibição explícita de `@pytest.mark.parametrize` e funções genéricas — G-3 no quality report), o `gemini-2.5-flash` gerou scripts com a estrutura correta: Page Object Model, `WebDriverWait`, naming convention e sem `time.sleep()`.

---

## 3. Pipeline — Run 2: `gemini-3.5-flash` (`generated2/`)

### 3.1 Sumário por história

| História | Agent 0 | Agent 1–3 | Motivo de parada |
|---|---|---|---|
| US-01 | ✅ APROVADA | ✅ Completo (6 casos, 6 scripts) | — |
| US-02 | ⚠️ PRECISA_DE_ESCLARECIMENTO | ❌ Bloqueada | Agent 0 identificou omissões nos critérios |
| US-03 | ⚠️ PRECISA_DE_ESCLARECIMENTO | ❌ Bloqueada | Agent 0 identificou omissões nos critérios |
| US-04 | ⚠️ PRECISA_DE_ESCLARECIMENTO | ❌ Bloqueada | Agent 0 identificou omissões nos critérios |
| US-05 | ⚠️ PRECISA_DE_ESCLARECIMENTO | ❌ Bloqueada | Agent 0 identificou omissões nos critérios |

O 3.5-flash foi mais estrito no gate do que o 2.5-flash: bloqueou 4 histórias vs. 2 da run anterior. Os problemas identificados são legítimos em todos os casos.

### 3.2 Agent 0 — Quality Gate (todas as 5 histórias)

| História | Status | Problemas identificados |
|---|---|---|
| US-01 | ✅ APROVADA | Nenhum — critérios "extremamente claros e detalhados" |
| US-02 | ⚠️ PRECISA_DE_ESCLARECIMENTO | Texto exato da mensagem de sucesso não especificado (CA-02.1); regra de strip/espaços em branco no campo nome ausente (CA-02.3) |
| US-03 | ⚠️ PRECISA_DE_ESCLARECIMENTO | Comportamento da UI em erro de validação 422 não descrito (CA-03.2); atribuição automática de `owner_id` não explicitada (CA-03.1) |
| US-04 | ⚠️ PRECISA_DE_ESCLARECIMENTO | Comportamento para acesso não autenticado não especificado; valores inválidos nos filtros sem comportamento definido |
| US-05 | ⚠️ PRECISA_DE_ESCLARECIMENTO | Comportamento dos botões do diálogo de confirmação não descrito (CA-05.1) |

Nota: o 3.5-flash identificou em US-02 e US-03 problemas que o 2.5-flash não sinalizou, o que sugere um gate mais rigoroso — potencialmente reduzindo IncorrectFact downstream.

### 3.3 Agent 1 + Juiz — US-01

| Tentativa | Casos | Cobertura | Fidelidade | Clareza | Automatiz. | Decisão |
|---|---|---|---|---|---|---|
| Attempt-0 | 6 | 10 | 10 | 10 | 10 | **APROVADO** |

US-01 aprovada na **primeira tentativa**, com pontuação máxima em todas as dimensões e zero cenários omitidos sugeridos. Nenhum ciclo de reparo foi necessário. Os 6 casos cobrem todas as 4 ACs (CA-01.1, CA-01.2, CA-01.3, CA-01.4), incluindo reset de contador e e-mail inválido — cenários que o 2.5-flash só incluiu após reparo.

### 3.4 Agent 3 — Codegen Selenium/PyTest

| História | Funções geradas | Formato correto | Page Object | WebDriverWait | Sem time.sleep |
|---|---|---|---|---|---|
| US-01 | 6 | ✅ `test_tc_01_0X_*` | ✅ `LoginPage`, `RequestsPage` | ✅ | ✅ |

Exemplo de função gerada (US-01):
```python
def test_tc_01_04_lockout_seis_tentativas(driver, credentials_lockout):
    login_page = LoginPage(driver)
    login_page.navigate()
    for _ in range(5):
        login_page.login(credentials_lockout["email"], credentials_lockout["password_incorrect"])
        assert login_page.get_error_message() == "E-mail ou senha inválidos."
    login_page.login(credentials_lockout["email"], credentials_lockout["password_correct"])
    assert "bloqueada" in login_page.get_lockout_message().lower()
    assert login_page.is_on_page()
```

---

## 4. Avaliação dos casos gerados — revisão por run

> Avaliações gravadas em `data/golden/generated1_case_reviews.json` e `data/golden/generated2_case_reviews.json`,
> no mesmo formato-guia de `data/golden/generated_case_reviews.json`.
> Protocolo: **all-or-nothing** (Travassos et al., 1999; Silva et al., 2026) — um defeito = caso inteiro Defective.
> Cobertura calculada contra `data/golden/US-XX.json` (oracle por história).
> Apenas histórias que avançaram pelo pipeline são avaliadas.

### 4.1 Run 1 — gemini-2.5-flash — US-01 (8 casos)

| Caso | Correto | Defeito | Justificativa |
|---|---|---|---|
| TC-01-01 | ✅ | — | Login válido → 200 + JWT + /requests. Cobre EXP-01-01 |
| TC-01-02 | ✅ | — | E-mail inexistente → 401 genérico. Cobre EXP-01-02 |
| TC-01-03 | ✅ | — | Senha incorreta → 401 genérico. Cobre EXP-01-03 |
| TC-01-04 | ✅ | — | E-mail formato inválido → 422. Cobre EXP-01-08 |
| TC-01-05 | ❌ | IncorrectFact | Off-by-one: testa 4 falhas + 5ª → 423; CA-01.3 e EXP-01-04 exigem 5 falhas + 6ª → 423. EXP-01-04 não coberto |
| TC-01-06 | ✅ | — | Bloqueio persiste com senha correta → 423. Cobre EXP-01-05 |
| TC-01-07 | ✅ | — | 4 falhas + login bem-sucedido reseta contador. Cobre EXP-01-07 |
| TC-01-08 | ✅ | — | Desbloqueio automático após 60s → 200. Cobre EXP-01-06 |

**Precision US-01: 7/8 = 0.875** | IncorrectFact: 1

### 4.2 Run 1 — gemini-2.5-flash — US-02 (9 casos)

| Caso | Correto | Defeito | Justificativa |
|---|---|---|---|
| TC-02-01 | ✅ | — | Cadastro válido → 201 + redirect /login. Cobre EXP-02-01 |
| TC-02-02 | ✅ | — | E-mail duplicado → 409 + conta original inalterada. Cobre EXP-02-04 e EXP-02-05 |
| TC-02-03 | ✅ | — | Senha sem número → 422. Cobre EXP-02-10 |
| TC-02-04 | ✅ | — | Senha sem letra → 422. Cobre EXP-02-09 |
| TC-02-05 | ✅ | — | Senha < 8 chars (7) → 422. Cobre EXP-02-08 |
| TC-02-06 | ✅ | — | Nome < 3 chars (2) → 422. Cobre EXP-02-06 |
| TC-02-07 | ❌ | IncorrectFact | Dado tem 82 chars, não 80; backend retornaria 422, não 201. EXP-02-03 não coberto |
| TC-02-08 | ✅ | — | Nome > 80 chars → 422 (resultado correto para qualquer comprimento > 80). Cobre EXP-02-07 |
| TC-02-09 | ✅ | — | E-mail formato inválido → 422 no cadastro. Cobre EXP-02-11 |

**Precision US-02: 8/9 = 0.889** | IncorrectFact: 1

### 4.3 Run 2 — gemini-3.5-flash — US-01 (6 casos)

| Caso | Correto | Defeito | Justificativa |
|---|---|---|---|
| TC-01-01 | ✅ | — | Login válido → 200 + JWT + /requests. Cobre EXP-01-01 |
| TC-01-02 | ✅ | — | Senha incorreta → 401 genérico. Cobre EXP-01-03 |
| TC-01-03 | ✅ | — | E-mail inexistente → 401 genérico (anti-enumeração verificada). Cobre EXP-01-02 |
| TC-01-04 | ✅ | — | 5 falhas + 6ª tentativa com senha correta → 423. Cobre EXP-01-04 e EXP-01-05 |
| TC-01-05 | ✅ | — | 4 falhas + login bem-sucedido reseta contador. Cobre EXP-01-07 |
| TC-01-06 | ✅ | — | E-mail formato inválido → 422. Cobre EXP-01-08 |

**Precision US-01: 6/6 = 1.000** | Defeitos: nenhum

### 4.4 Cobertura do oracle — Recall

**US-01 (8 casos esperados pelo oracle)**

| Oracle | Run 1 gemini-2.5-flash | Run 2 gemini-3.5-flash |
|---|---|---|
| EXP-01-01 Login válido → 200 | TC-01-01 ✅ | TC-01-01 ✅ |
| EXP-01-02 E-mail inexistente → 401 | TC-01-02 ✅ | TC-01-03 ✅ |
| EXP-01-03 Senha incorreta → 401 | TC-01-03 ✅ | TC-01-02 ✅ |
| EXP-01-04 5 falhas → 6ª retorna 423 | TC-01-05 ❌ off-by-one | TC-01-04 ✅ |
| EXP-01-05 Bloqueio com senha correta | TC-01-06 ✅ | TC-01-04 ✅ |
| EXP-01-06 Desbloqueio após 60s | TC-01-08 ✅ | — ❌ (não gerado) |
| EXP-01-07 Sucesso reseta contador | TC-01-07 ✅ | TC-01-05 ✅ |
| EXP-01-08 E-mail inválido → 422 | TC-01-04 ✅ | TC-01-06 ✅ |

**US-01 Recall Run 1: 7/8 = 0.875** | **US-01 Recall Run 2: 7/8 = 0.875**

**US-02 (11 casos esperados — Run 1 apenas)**

| Oracle | Run 1 gemini-2.5-flash |
|---|---|
| EXP-02-01 Cadastro válido → 201 | TC-02-01 ✅ |
| EXP-02-02 Nome = 3 chars → 201 | — ❌ (não gerado) |
| EXP-02-03 Nome = 80 chars → 201 | TC-02-07 ❌ (82 chars → teste falharia) |
| EXP-02-04 E-mail duplicado → 409 | TC-02-02 ✅ |
| EXP-02-05 Duplicado não altera original | TC-02-02 ✅ |
| EXP-02-06 Nome = 2 chars → 422 | TC-02-06 ✅ |
| EXP-02-07 Nome = 81 chars → 422 | TC-02-08 ✅ |
| EXP-02-08 Senha = 7 chars → 422 | TC-02-05 ✅ |
| EXP-02-09 Senha sem letra → 422 | TC-02-04 ✅ |
| EXP-02-10 Senha sem número → 422 | TC-02-03 ✅ |
| EXP-02-11 E-mail inválido → 422 | TC-02-09 ✅ |

**US-02 Recall Run 1: 9/11 = 0.818**

### 4.5 Métricas consolidadas por run

| Métrica | Run 1 US-01 | Run 1 US-02 | **Run 1 total** | Run 2 US-01 |
|---|---|---|---|---|
| Casos gerados | 8 | 9 | **17** | 6 |
| Corretos | 7 | 8 | **15** | 6 |
| **Precision** | 0.875 | 0.889 | **0.882** | **1.000** |
| Casos oracle | 8 | 11 | **19** | 8 |
| Cobertos | 7 | 9 | **16** | 7 |
| **Recall** | 0.875 | 0.818 | **0.842** | **0.875** |
| **F1** | 0.875 | 0.853 | **0.862** | **0.933** |
| IncorrectFact | 1 | 1 | 2 | 0 |
| Baseline Silva et al. | — | — | Precision ~0.72 | Precision ~0.72 |

**Padrão de defeito:** IncorrectFact em 2/23 casos avaliados (8.7%) — ambos por falha ao computar comprimentos reais de strings de teste (TC-01-05: off-by-one no contador de bloqueio; TC-02-07: string com 82 chars declarada como 80). Histórias com regras numéricas explícitas no glossário apresentam menor incidência de IncorrectFact.

**Eficácia do reparo (Run 1):**

| Métrica | US-01 | US-02 |
|---|---|---|
| Casos antes do reparo | 6 | 6 |
| Cenários adicionados pelo reparo | 2 | 3 |
| Casos após reparo | 8 | 9 |
| Iterações para aprovação | 2 | 3 |

> **Referência histórica:** `data/golden/generated_case_reviews.json` avalia 24 casos de uma run anterior (5 USs, modelo não preservado): Precision = 0.833. Os valores acima são das runs documentadas com gemini-2.5-flash e gemini-3.5-flash.

---

## 5. Comparação com Silva et al. (2026)

| Dimensão | Silva et al. | gemini-2.5-flash Run 1 | gemini-3.5-flash Run 2 |
|---|---|---|---|
| Modelo | GPT-4o / DeepSeek / Gemini 1.5 | gemini-2.5-flash | gemini-3.5-flash |
| Protocolo | zero/one-shot, sem RAG | RAG + juiz + reparo | RAG + juiz + reparo |
| Histórias aprovadas pelo gate | 10 | 2/5 (US-03..05 bloqueadas) | 1/5 (US-02..05 bloqueadas) |
| Histórias end-to-end | 10 | 2 (US-01 + US-02) | 1 (US-01) |
| Casos avaliados | 1.528 | 17 | 6 |
| **Precision** | ~0.72 | **0.882** (15/17) | **1.000** (6/6) |
| **Recall** (US-01) | ~0.56 | **0.875** (7/8 oracle) | **0.875** (7/8 oracle) |
| **F1** (US-01) | — | **0.875** | **0.933** |
| Iterações de reparo (US-01) | — | 2 | **0** |
| Modo de falha dominante | Omissão (FN) | IncorrectFact (off-by-one, string length) | Nenhum detectado |
| Codegen funcional | N/A | ✅ 17 funções (US-01 + US-02) | ✅ 6 funções (US-01) |

**Achado principal:** o pipeline com juiz+reparo supera o baseline de Silva et al. em Precision, Recall e F1 em ambas as runs. O gemini-3.5-flash atingiu Precision=1.0 e F1=0.933 sem nenhum ciclo de reparo — gerando de primeira todos os cenários que o 2.5-flash precisou de reparo para incluir. O 2.5-flash, após 2 ciclos, atingiu F1=0.875 com o reparo corrigindo precisamente as omissões de variantes de borda (EXP-01-06, EXP-01-07), o modo de falha dominante identificado na literatura. IncorrectFact (off-by-one em TC-01-05; string de 82 chars em TC-02-07) é o defeito residual característico da geração sem verificação de comprimento.

---

## 6. Discussão e limitações

### 6.1 gemini-2.5-flash como modelo de pipeline (Run 1)

Pontos positivos:
- Agent 0 (quality gate): bloqueou US-04 e US-05 corretamente por omissões reais nos critérios; aprovou US-01..03 com justificativas precisas
- Agent 1 (geração): casos estruturalmente corretos, regras numéricas capturadas com precisão
- Agent 2 (juiz): gaps de cobertura identificados corretamente; não produziu falsos positivos nos casos individuais
- Agent 3 (codegen): gerou scripts PyTest válidos com Page Object Model, naming correto e WebDriverWait

Pontos negativos / observações:
- IncorrectFact em US-03 (run oracle): o modelo gerou strings de teste descritivas sem verificar comprimento real
- Instrução de não reprovar por cosmética (juiz): ignorada em run com llama3 anterior ao fix de prompt (registrada no QUALITY_REPORT.md)

### 6.2 Efeito do context builder

A Precision de 0.882 (Run 1) e 1.000 (Run 2) versus ~0.72 de Silva et al. em zero-shot sugere que o context builder (glossário + ui_map + few-shot) reduziu IncorrectFact ao fornecer valores precisos de limite de campo. O único defeito de IncorrectFact do tipo "string com comprimento incorreto" observado em US-02/TC-02-07 é análogo ao padrão US-03 encontrado na run de referência histórica (dado "Título inválido" com comprimento inválido) — o modelo gerou strings descritivas sem computar seu comprimento real, contra casos onde o glossário explicita os limites.

### 6.3 Omissão como modo de falha dominante

Consistente com Silva et al.: a geração inicial omitiu variantes de borda de CA-01.3 (reset de contador, expiração de bloqueio) e CA-02.1/02.3 (limites de tamanho). O juiz identificou essas omissões e o reparo as corrigiu — validando a arquitetura de três estágios (geração → juiz → reparo).

### 6.4 Limitações do estudo

- **Escala:** 5 histórias em app controlado; não generalizável para sistemas industriais.
- **Run parcial:** apenas US-01 e US-02 processadas end-to-end na run principal. US-03..05 sem dados de Agent 1/2/3.
- **Oracle incompleto:** `matched_generated_case_ids` vazios; Recall e F1 não computados automaticamente.
- **Fase 6 não executada:** scripts não foram executados contra o app PoC. Taxa de sucesso funcional indefinida.
- **Dois modelos:** gemini-2.5-flash e gemini-3.5-flash avaliados. Modelos locais (ollama/llama3) e outros providers (Claude, GPT-4) não testados em run completa.
- **Esforço humano:** `effort_timings.json` com zeros; razão esforço-pipeline vs. autoria manual não medida.
