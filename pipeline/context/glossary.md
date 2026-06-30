# Glossário de Domínio — PoC App

Vocabulário e regras de negócio do sistema de solicitações usado como cobaia
pelo pipeline de QA. Fonte de verdade para os agentes (Agentes 0–3 e
Sumarizador) sobre o que cada termo significa no contexto deste PoC.

> Mantido propositalmente curto. Excesso de contexto piora geração (Correia et
> al., 2025). Inclui apenas o que evita ambiguidade ou inferência errada por
> parte do LLM.

---

## 1. Entidades

**Usuário.** Pessoa cadastrada no sistema. Atributos: `id`, `name`, `email`
(único), `password_hash`, `created_at`. Campos de política de bloqueio:
`failed_login_attempts`, `locked_until`.

**Solicitação de serviço** (*service request*). Pedido aberto por um usuário.
Atributos: `id`, `title`, `description`, `priority`, `status`, `created_at`,
`cancelled_at` (nulo até o cancelamento), `owner_id`. Toda solicitação tem
exatamente um dono.

---

## 2. Enumerações

**Status da solicitação** (`RequestStatus`):

| Valor (DB) | Apresentação UI | Significado |
|---|---|---|
| `aberta` | "aberta" | Recém-criada, ainda não processada. Cancelável. |
| `em_analise` | "em análise" | Em triagem. Cancelável. |
| `cancelada` | "cancelada" | Cancelada pelo dono. Terminal. |
| `finalizada` | "finalizada" | Concluída pela operação. Terminal. |

> No banco a string é `em_analise` (sem acento e com underscore) para evitar
> problemas de encoding em queries. Na UI aparece como "em análise".

**Prioridade** (`RequestPriority`): `baixa`, `media`, `alta`. Na UI `media`
aparece como "média".

---

## 3. Regras de negócio explícitas

**Política de bloqueio (lockout).** Após **5 tentativas de login falhas
consecutivas** para um mesmo e-mail, a conta fica **bloqueada por 60 segundos**.
Login bem-sucedido zera o contador. Durante o bloqueio, qualquer tentativa
(mesmo com senha correta) é rejeitada.

**Anti-enumeração de usuários.** A mensagem de erro em falha de credencial é
sempre a mesma — `"E-mail ou senha inválidos."` — independentemente de o
e-mail existir ou não. Isso impede que atacantes descubram contas pelo erro.

**Regra de propriedade (ownership).** Um usuário só pode listar, visualizar,
cancelar ou modificar solicitações próprias. Tentar agir sobre solicitação de
outro retorna 403.

**Cancelabilidade.** Apenas solicitações em status `aberta` ou `em_analise`
podem ser canceladas. Tentar cancelar `cancelada` ou `finalizada` retorna 409.
Cancelar seta `status = cancelada` e `cancelled_at = agora()`; bloqueia
edições posteriores.

**Lista padrão.** A listagem de solicitações por padrão (`scope=own`) retorna
apenas as do próprio usuário, ordenadas por `created_at` descendente (mais
recentes primeiro).

**Resultado vazio não é erro.** Lista sem itens retorna `200 OK` com `items=[]`.
A UI exibe "Nenhuma solicitação encontrada" **sem esconder os filtros**.

**Status e data automáticos.** Ao criar uma solicitação, `status` é definido
pelo servidor como `aberta` e `created_at` é o instante do servidor. Cliente
não pode sobrescrever.

---

## 4. Regras de validação por campo

| Entidade | Campo | Regra | Onde |
|---|---|---|---|
| Registro | `name` | 3–80 caracteres, não vazio após strip | `RegisterIn` |
| Registro | `email` | formato de e-mail válido; único | `RegisterIn` + DB unique |
| Registro | `password` | ≥8 caracteres; ao menos 1 letra E 1 número | `RegisterIn.password_complexity` |
| Login | `email` | formato válido (mas a resposta não diferencia) | `LoginIn` |
| Login | `password` | qualquer string (validado contra hash) | `LoginIn` |
| Solicitação | `title` | 5–100 caracteres, não vazio após strip | `RequestCreateIn` |
| Solicitação | `description` | 10–500 caracteres, não vazio após strip | `RequestCreateIn` |
| Solicitação | `priority` | obrigatoriamente um valor do enum | `RequestCreateIn` |

> Falha de validação retorna **422 Unprocessable Entity** pelo FastAPI/Pydantic.

---

## 5. Semântica HTTP usada pela API

| Código | Quando | Detalhe relevante para testes |
|---|---|---|
| 200 | Sucesso (`GET`, `POST cancel`, `POST login`) | Corpo: recurso ou token |
| 201 | Criação (`POST register`, `POST requests`) | Corpo: recurso criado |
| 401 | Credencial inválida no login | `detail = "E-mail ou senha inválidos."` (mensagem fixa) |
| 403 | Tentativa de agir sobre recurso de outro usuário | `detail = "Você não pode cancelar uma solicitação de outro usuário."` |
| 404 | Recurso inexistente | `detail = "Solicitação não encontrada."` |
| 409 | Conflito | E-mail duplicado: `"E-mail já cadastrado."` · Status não cancelável: `"Somente solicitações 'aberta' ou 'em análise' podem ser canceladas."` |
| 422 | Falha de validação Pydantic | Corpo segue formato do FastAPI: `{ "detail": [ {loc, msg, type}, ... ] }` |
| 423 | Conta bloqueada por lockout | Header `Retry-After: <segundos>`; `detail = "Conta bloqueada. Tente novamente em N segundos."` |

---

## 6. Autenticação

- **Esquema**: Bearer JWT no header `Authorization: Bearer <token>`.
- **Emissão**: `POST /api/auth/login` retorna `{ access_token, token_type:"bearer", user }`.
- **Validade**: configurável via `JWT_EXPIRES_HOURS` (default 8h).
- **Endpoints protegidos**: todos sob `/api/requests/*` e `/api/auth/me`.
- **Sem refresh token** (escopo de PoC).

---

## 7. Vocabulário UX e de testes

**`data-testid`.** Atributo HTML colocado em todo elemento interativo do
frontend. É o seletor preferido pelos scripts Selenium gerados pelo Agente 3
porque sobrevive a mudanças visuais. Catálogo em `pipeline/context/ui_map.json`.

**Empty state.** Mensagem exibida quando uma lista está vazia. No PoC é
sempre `"Nenhuma solicitação encontrada."` com os controles de filtro
permanecendo visíveis (não esconder filtros é critério de aceitação da US-04).

**Confirm dialog.** Diálogo modal de confirmação exibido antes de ações
destrutivas. No PoC, apenas o cancelamento de solicitação tem dialog
(US-05). O dialog mostra o **título** da solicitação a ser cancelada.

**Caso positivo / negativo / de borda.** Vocabulário usado pelo Agente 1:
- *Positivo*: caminho feliz; entrada válida que produz sucesso.
- *Negativo*: entrada inválida que deve ser rejeitada (validação, conflito).
- *Borda*: limites de validação (e.g. exatamente 80 caracteres no nome), regras
  de segurança (e.g. anti-enumeração), e condições de transição (lockout
  ativando, status terminal).

---

## 8. Dados de seed (sempre disponíveis)

O banco é recriado em todo start do backend (`RESET_DB_ON_STARTUP=1`).
Existem dois usuários com senha `Senha123`:

| E-mail | Notas |
|---|---|
| `alice@example.com` | 4 solicitações cobrindo os 4 status e 3 prioridades. Preferida para US-04 e US-05. |
| `bob@example.com` | 2 solicitações (`aberta`/alta e `em_analise`/baixa). Usada para verificar regra de propriedade. |

> ⚠️ Se um teste de lockout rodar contra `alice@example.com`, ela ficará
> bloqueada por 60s. Testes paralelos devem usar usuários distintos ou um
> registro novo via `POST /api/auth/register`.
