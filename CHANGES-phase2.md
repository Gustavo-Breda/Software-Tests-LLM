# Fase 2 — Context assets & Context Builder

Entregue conforme `docs/PLAN.md §5` (Phase 2 done-check).

## O que foi adicionado

| Arquivo | Função |
|---|---|
| `pipeline/context/glossary.md` | Glossário de domínio PT-BR: entidades, enums de status/prioridade, regras de negócio explícitas (lockout, ownership, cancelabilidade, anti-enumeração), validações por campo, semântica HTTP, autenticação, vocabulário UX/testes, dados de seed |
| `pipeline/context/context_builder.py` | Implementação principal. Carrega glossário + `ui_map.json` + examples + stories, filtra por story, monta um *context blob* markdown |
| `pipeline/context/test_context_builder.py` | Done-check da fase. Roda o builder contra as 5 stories e valida estrutura + presença dos critérios + presença de seletores |
| `pipeline/context/examples/example_us02_registration.json` | Exemplo gold-standard de saída do Agente 1 — usado como few-shot. 4 casos de teste cobrindo positivo/negativo/borda no formato exato do contrato em `PLAN.md §7` |
| `pipeline/context/__init__.py` | Marcador de pacote Python |
| `data/user_stories/US-01.yaml` … `US-05.yaml` | 5 stories estruturadas em YAML: persona/ação/benefício + 3 critérios de aceitação cada (`CA-XX.Y`) marcados como `positivo`, `negativo` ou `borda` |

## O que foi modificado

| Arquivo | Mudança |
|---|---|
| `pipeline/requirements.txt` | Adicionado `pyyaml>=6.0,<7.0` (stories são YAML) |
| `docs/PLAN.md` | Checkboxes da Fase 2 marcados como `[x]` |
| `AGENTS.md` | Banner de estágio do repo e tabela de estado atualizados |

## O que NÃO foi modificado (intencionalmente)

- `pipeline/context/ui_map.json` — já existia da Fase 1 e bate 1:1 com os
  `data-testid` no frontend React. Verifiquei com `grep`: 34 seletores no
  frontend = 34 documentados no ui_map.
- `pipeline/llm/*` — não tocado pela Fase 2.
- `pipeline/workflow/runner.py` — será atualizado na Fase 3 para invocar
  o Context Builder antes do Agente 0.
- `app/backend/*`, `app/frontend/*` — Fase 1, intocados.

## Princípios de design

Os documentos do projeto (README, PLAN, AGENTS) citam Correia et al. (2025)
sobre o risco de *RAG não-curado* aumentar a verbosidade dos prompts e
piorar a geração. O builder lida com isso assim:

1. **Filtragem agressiva por story.** Cada blob só recebe os endpoints e telas
   que aquela story toca. `ui_map.json` tem 5 telas / 7 endpoints; o blob de
   US-01 (login) só carrega 2 telas e 2 endpoints; o blob de US-05 (cancelar)
   carrega 2 telas e 2 endpoints. Sem filtragem o blob ficaria ~50% maior.
2. **Glossário completo, mas curto.** O glossário inteiro é incluído porque
   é compacto (~5 KB) e o vocabulário é coeso — fatiar entidades/regras por
   story criaria inconsistências mais fáceis de errar do que de prevenir.
3. **Um único exemplo few-shot.** Mais exemplos = mais tokens sem ganho
   marginal claro. Se cobertura ficar ruim, dá pra adicionar exemplos
   específicos por story depois.
4. **Ordem das seções.** Vocabulário (glossário) → referências concretas
   (API, UI, seed) → exemplo (formato) → tarefa (story + critérios). LLM lê
   tudo antes de "ver" o que precisa fazer.

## Como validar localmente

```bash
# via Docker (recomendado)
docker compose run --rm pipeline python -m pipeline.context.test_context_builder

# ou em ambiente local com pyyaml instalado
python -m pipeline.context.test_context_builder
```

Saída esperada termina com: `Todas as stories produziram blobs completos. ✅`.

## Como inspecionar um blob

```bash
# imprime o blob de uma story específica
python -m pipeline.context.context_builder US-03

# imprime todas
python -m pipeline.context.context_builder --all

# lista IDs disponíveis
python -m pipeline.context.context_builder --list
```

## Estatísticas dos blobs gerados (estado atual)

| Story | Chars | ~Tokens | Critérios |
|---|---:|---:|---:|
| US-01 | 14758 | 3689 | 3 |
| US-02 | 14523 | 3630 | 3 |
| US-03 | 14874 | 3718 | 3 |
| US-04 | 14557 | 3639 | 3 |
| US-05 | 14815 | 3703 | 3 |

Tamanhos consistentes entre stories (variação <2.5%) — sinal de que a
filtragem não introduz vieses por story.

## API pública do `ContextBuilder`

```python
from pipeline.context.context_builder import ContextBuilder

# bind no layout padrão do repo
builder = ContextBuilder.from_repo()

# ou explicitamente
builder = ContextBuilder(
    glossary_path=Path("pipeline/context/glossary.md"),
    ui_map_path=Path("pipeline/context/ui_map.json"),
    examples_dir=Path("pipeline/context/examples"),
    stories_dir=Path("data/user_stories"),
)

# listar stories disponíveis
builder.list_stories()             # → ["US-01", ..., "US-05"]

# carregar uma story (dataclass UserStory)
story = builder.load_story("US-03")

# construir o blob (uma story ou todas)
blob  = builder.build("US-03")     # → ContextBlob
blobs = builder.build_all()        # → list[ContextBlob]

# propriedades do blob
blob.text             # markdown completo, pronto pra injetar no prompt
blob.char_count       # tamanho em chars
blob.token_estimate   # heurística (chars // 4)
blob.section_titles() # lista de seções
```

## Próximos passos (Fase 3)

O Context Builder deixa o terreno preparado para os Agentes 0 e 1.
A integração natural será no `pipeline/workflow/runner.py`:

```python
from pipeline.context.context_builder import ContextBuilder
from pipeline.llm.factory import get_client

builder = ContextBuilder.from_repo()
client  = get_client(f"{provider}:{model}")

for story in builder.build_all():
    # Agente 0: passa só story + critérios (gate é sobre qualidade da story)
    gate_verdict = run_agent0(client, story)
    if gate_verdict["status"] != "APROVADA":
        continue
    # Agente 1: recebe o blob completo de contexto
    test_cases = run_agent1(client, story.text)
    ...
```

`story.text` é o blob renderizado; basta concatenar com o prompt do agente.
