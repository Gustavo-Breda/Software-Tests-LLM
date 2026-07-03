# Relatorio Fake de Execucao End-to-End

## Objetivo

Este documento simula um ciclo completo do pipeline para as 5 user stories do projeto, incluindo:

- Agent 0 aprovando historias.
- Agent 1 gerando casos.
- Agent 2 reprovando parte dos casos e disparando repair loop.
- Agent 3 gerando scripts.
- Execucao ilustrativa com classificacao de falhas.
- Comparacao final com o oraculo humano em `data/golden/`.
- Calculo de metricas de qualidade e esforco.

Premissa:

- Relatorio ficticio, mas aderente ao contrato do projeto.
- Oraculo real usado como referencia: `data/golden/US-01.json` a `data/golden/US-05.json`.
- Meta nao foi 100% de acerto. Foram mantidas omissoes e alguns casos incorretos para produzir metricas realistas.

## Resumo Executivo

| Item | Resultado |
|---|---:|
| User stories avaliadas | 5 |
| Casos gerados no final do pipeline | 29 |
| Casos corretos segundo oraculo | 26 |
| Casos esperados no oraculo | 51 |
| Casos esperados cobertos | 32 |
| Precision | 0.8966 |
| Recall | 0.6275 |
| F1 | 0.7382 |
| Omission rate | 0.3725 |
| Incorrect-fact rate | 0.1034 |
| Cobertura de criterios de aceitacao | 1.0 |
| Script collect rate | 1.0 |
| Judge precision | 0.8000 |
| Judge recall | 0.7273 |
| Razao esforco manual/pipeline | 2.5 |

## Fluxo Simulado por User Story

### US-01

- Agent 0: `APROVADA`.
- Agent 1 inicial: 5 casos.
- Agent 2 reprovou 1 caso.
- Repair loop corrigiu 1 caso.
- Agent 3 gerou 5 scripts.

Detalhe do repair:

- `TC-01-04` foi reprovado porque descrevia lockout sem explicitar as 5 falhas consecutivas nem a verificacao do header `Retry-After`.
- Caso reparado `TC-01-04R` passou a validar a sequencia correta e foi aceito pelo judge.

Estado final:

- 5 casos finais.
- 5 corretos contra o oraculo.
- 3 cenarios do oraculo ficaram omitidos:
  - expiracao do lockout apos 60s
  - persistencia do lockout mesmo com senha correta
  - reset do contador apos login bem-sucedido

### US-02

- Agent 0: `APROVADA`.
- Agent 1 inicial: 6 casos.
- Agent 2 reprovou 1 caso por cobertura insuficiente de fronteira positiva.
- Repair loop adicionou 1 caso aprovado.
- Agent 3 gerou 7 scripts.

Detalhe do repair:

- O judge apontou ausencia do limite inferior valido de nome.
- Foi adicionado `TC-02-05R` para nome com exatamente 3 caracteres.

Divergencia mantida de proposito:

- `TC-02-07` foi aceito pelo pipeline, mas esta errado frente ao oraculo. Ele exige caractere especial na senha, regra que nao existe no sistema. Classificacao: `IncorrectFact`.

Estado final:

- 7 casos finais.
- 6 corretos contra o oraculo.
- 4 cenarios omitidos:
  - nome com 80 caracteres aceito
  - nome com 81 caracteres rejeitado
  - senha com 7 caracteres rejeitada
  - senha sem letra rejeitada

### US-03

- Agent 0: `APROVADA`.
- Agent 1 inicial: 7 casos.
- Agent 2 reprovou 4 casos.
- Repair loop corrigiu 3 casos e aprovou 1 novo caso de API sem autenticacao.
- Agent 3 gerou 6 scripts finais.

Detalhe do repair:

- `TC-03-02` dizia testar titulo curto, mas usava string dentro da faixa valida. Foi corrigido para titulo com 4 caracteres.
- `TC-03-03` dizia testar descricao curta, mas usava string valida. Foi corrigido para descricao com 9 caracteres.
- `TC-03-05` tentava validar `401` pela UI em rota protegida. Foi convertido em caso de API sem `Authorization`.

Divergencia mantida de proposito:

- `TC-03-06` passou pelo judge, mas ficou incorreto: esperava `403` para JWT expirado, enquanto o oraculo espera `401`. Classificacao: `IncorrectFact`.

Estado final:

- 6 casos finais.
- 5 corretos contra o oraculo.
- 10 cenarios omitidos, principalmente limites superiores/ inferiores positivos e fluxos de token invalido/expirado.

### US-04

- Agent 0: `APROVADA`.
- Agent 1 inicial: 4 casos.
- Agent 2 reprovou 1 caso de empty state.
- Repair loop corrigiu 1 caso.
- Agent 3 gerou 5 scripts.

Detalhe do repair:

- Caso inicial de lista vazia assumia que `status=cancelada` retornaria zero itens para `alice`, o que contradiz o seed.
- `TC-04-04R` passou a usar combinacao de filtros sem correspondencia real e foi aprovado.

Divergencia mantida de proposito:

- `TC-04-05` introduziu paginação obrigatoria de 10 itens por pagina, regra nao descrita na historia nem no oraculo. Classificacao: `IncorrectFact`.

Estado final:

- 5 casos finais.
- 4 corretos contra o oraculo.
- 2 cenarios omitidos:
  - isolamento explicito por `priority=alta`
  - ausencia de dados de outros usuarios em verificacao dedicada

### US-05

- Agent 0: `APROVADA`.
- Agent 1 inicial: 6 casos.
- Agent 2 reprovou 1 caso por falta de verificacao de `cancelled_at`.
- Repair loop corrigiu o caso.
- Agent 3 gerou 6 scripts.

Detalhe do repair:

- `TC-05-01` foi ajustado para verificar:
  - exibicao do titulo no dialog antes do POST
  - persistencia conjunta de `status='cancelada'` e `cancelled_at`

Estado final:

- 6 casos finais.
- 6 corretos contra o oraculo.
- Nenhuma omissao relevante no nivel de criterio. Todos os 8 cenarios esperados ficaram cobertos por 6 casos bem desenhados.

## Comparacao com Oraculo Humano

Base:

- `data/golden/US-01.json`
- `data/golden/US-02.json`
- `data/golden/US-03.json`
- `data/golden/US-04.json`
- `data/golden/US-05.json`

| US | Casos gerados | Casos corretos | Casos esperados | Esperados cobertos | Omitidos | Casos espurios/incorretos |
|---|---:|---:|---:|---:|---:|---:|
| US-01 | 5 | 5 | 8 | 5 | 3 | 0 |
| US-02 | 7 | 6 | 11 | 7 | 4 | 1 |
| US-03 | 6 | 5 | 16 | 6 | 10 | 1 |
| US-04 | 5 | 4 | 8 | 6 | 2 | 1 |
| US-05 | 6 | 6 | 8 | 8 | 0 | 0 |
| **Total** | **29** | **26** | **51** | **32** | **19** | **3** |

Casos incorretos mantidos para gerar metricas:

| Caso | Tipo de defeito | Motivo |
|---|---|---|
| `TC-02-07` | `IncorrectFact` | Exige caractere especial na senha, regra inexistente. |
| `TC-03-06` | `IncorrectFact` | Espera `403` para JWT expirado; oraculo espera `401`. |
| `TC-04-05` | `IncorrectFact` | Assume paginação obrigatoria de 10 itens, regra nao especificada. |

## Execucao Ilustrativa e Sumario de Falhas

Esta parte representa a fase de execucao + summarizer. Nao foi usada para precision/recall do oracle, mas ajuda a demonstrar o ciclo completo.

Resumo de execucao:

- 29 scripts gerados.
- 29 scripts coletados com sucesso.
- 26 passaram.
- 3 falharam.

Classificacao resumida:

| Caso | Categoria | Descricao |
|---|---|---|
| `TC-03-06` | `teste` | Script implementa expectativa incorreta para JWT expirado. |
| `TC-04-04R` | `seletor` | Mudanca pontual de `data-testid` no empty state. |
| `TC-05-01R` | `sistema` | `cancelled_at` nao persistiu em uma execucao seedada. |

## Metricas Finais

### Qualidade dos Casos

| Metrica | Valor |
|---|---:|
| Precision | 0.8966 |
| Recall | 0.6275 |
| F1 | 0.7382 |
| Omission rate | 0.3725 |
| Incorrect-fact rate | 0.1034 |
| Acceptance-criteria coverage | 1.0000 |

Leitura:

- Precision alta: maioria dos casos finais ficou aderente ao sistema.
- Recall medio: pipeline ainda deixou varios cenarios do oraculo sem cobertura, sobretudo em fronteiras e autorizacao.
- Cobertura de criterio ficou 100%, mas isso nao significa cobertura de cenario. O pipeline tocou todos os criterios, mas nao esgotou todas as variacoes relevantes.

### Qualidade da Automacao

| Metrica | Valor |
|---|---:|
| Script collect rate | 1.0000 |
| Pending automation count | 3 |
| Functional success rate | 0.8966 |

Leitura:

- Geracao de script ficou robusta no nivel de sintaxe/coleta.
- Ainda existem 3 pendencias de automacao documentadas.
- Algumas falhas na execucao vieram de defeito no proprio caso ou de drift de seletor.

### Eficacia do Judge

| Metrica | Valor |
|---|---:|
| Problemas reportados pelo judge | 10 |
| Problemas confirmados por humano | 8 |
| Problemas humanos nao vistos pelo judge | 3 |
| Judge precision | 0.8000 |
| Judge recall | 0.7273 |

Leitura:

- Judge ajudou de forma relevante no repair loop.
- Ainda deixou passar 3 problemas humanos, inclusive dois `IncorrectFact`.

### Esforco Percebido

| Metrica | Valor |
|---|---:|
| Tempo de revisao com pipeline | 96 min |
| Tempo de autoria manual | 240 min |
| Razao manual/pipeline | 2.5000 |

Leitura:

- Fluxo com pipeline consumiu menos esforco humano total.
- Ganho veio de nao escrever tudo do zero, apesar da revisao e do repair loop.

## Conclusao

O resultado fake representa bem um cenario plausivel para apresentacao:

- pipeline agrega valor real
- judge melhora varios casos ruins do Agent 1
- mesmo com repair loop, ainda restam omissoes e alguns `IncorrectFact`
- comparacao com `data/golden/` mostra ganho, mas nao perfeicao
- automacao fica forte o bastante para demonstrar viabilidade tecnica

## Arquivo de Metricas

Versao estruturada deste relatorio:

- `generated/reports/fake_end_to_end_metrics.json`
