# PoC App — Fase 1

Aplicação proof-of-concept que o pipeline do QA Assistant tem como alvo.
Backend em **FastAPI + SQLite**; frontend em **Angular 18** (standalone components),
servido via **nginx**; tudo orquestrado por **Docker Compose**.

> Este README cobre a **Fase 1** do `plan.md`. Fases seguintes (Context Builder,
> agentes, codegen, execução, métricas) ainda não tocam neste app diretamente —
> elas leem o `ui_map.json` aqui e geram código em outro lugar do repositório.

---

## Sumário

1. [O que está incluído](#1-o-que-está-incluído)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Instalação dos pré-requisitos](#3-instalação-dos-pré-requisitos)
   - [Linux (Ubuntu/Debian)](#linux-ubuntudebian)
   - [macOS](#macos)
   - [Windows](#windows-10-11)
4. [Caminho A — Rodando via Docker (recomendado)](#4-caminho-a--rodando-via-docker-recomendado)
5. [Caminho B — Rodando em modo dev (sem Docker)](#5-caminho-b--rodando-em-modo-dev-sem-docker)
6. [Verificando que tudo funcionou](#6-verificando-que-tudo-funcionou)
7. [Credenciais e dados de seed](#7-credenciais-e-dados-de-seed)
8. [Endpoints da API](#8-endpoints-da-api)
9. [Smoke test (validação automática)](#9-smoke-test-validação-automática)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. O que está incluído

```
poc-app/
├── docker-compose.yml         # backend + frontend; selenium/ollama comentados p/ fases futuras
├── .env.example               # variáveis usadas pelo backend e (depois) pelo pipeline
├── ui_map.json                # contrato da API + seletores data-testid do frontend
├── backend/                   # FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── smoke_test.py          # 17 asserts cobrindo as regras das 5 user stories
│   └── app/
│       ├── main.py            # entrypoint (lifespan recria o banco)
│       ├── database.py
│       ├── models.py          # User, ServiceRequest
│       ├── schemas.py         # Pydantic com validação de campo
│       ├── security.py        # bcrypt + JWT; constantes de lockout
│       ├── seed.py            # dados determinísticos
│       ├── deps.py
│       └── routers/
│           ├── auth.py        # US-01 login + lockout, US-02 register
│           └── requests.py    # US-03 create, US-04 list+filter, US-05 cancel
└── frontend/                  # Angular 18 (standalone components)
    ├── Dockerfile             # multi-stage (build com Node, serve com nginx)
    ├── nginx.conf             # SPA fallback
    ├── package.json
    ├── angular.json
    └── src/
        ├── index.html
        ├── main.ts
        ├── styles.css
        ├── environments/      # apiBaseUrl (dev e prod)
        └── app/
            ├── app.component.ts
            ├── app.config.ts
            ├── app.routes.ts  # rotas lazy + guards
            ├── core/          # AuthService, RequestsService, guard, interceptor
            ├── models/        # tipos espelhando o backend
            └── pages/
                ├── login/     # US-01
                ├── register/  # US-02
                ├── list/      # US-04 + dialog de cancelar (US-05)
                └── create/    # US-03
```

---

## 2. Pré-requisitos

Duas opções, escolha **uma**:

| Caminho | O que precisa | Quando escolher |
|---|---|---|
| **A) Docker** (recomendado) | Docker Engine 24+ com Docker Compose v2 | Você quer só rodar e ver funcionando. Nada além de Docker. |
| **B) Dev local**            | Python 3.12+ e Node.js 20+ (22 testado) | Você quer hot-reload, depurar, mexer no código com mais facilidade. |

> Para a **Fase 1** o objetivo é só ter o app rodando — qualquer um dos caminhos
> serve. A partir da Fase 3 (pipeline) o Docker fica mais conveniente.

---

## 3. Instalação dos pré-requisitos

### Linux (Ubuntu/Debian)

**Docker** (caminho A):
```bash
# Remove instalações antigas
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# Instala via repositório oficial
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Habilita rodar docker sem sudo (precisa relogar depois)
sudo usermod -aG docker $USER

# Verifica
docker --version
docker compose version
```

**Python 3.12 + Node.js 22** (caminho B):
```bash
# Python
sudo apt install -y python3 python3-venv python3-pip
python3 --version   # deve ser 3.10+ idealmente 3.12

# Node via nvm (mais fácil que repositórios distros)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
# reabra o terminal e:
nvm install 22
node --version && npm --version
```

### macOS

**Docker** (caminho A):
- Baixe e instale **Docker Desktop**: <https://www.docker.com/products/docker-desktop>
- Abra o app uma vez (ele inicializa o engine).
- Verifique no terminal: `docker --version && docker compose version`.

Alternativa via Homebrew:
```bash
brew install --cask docker
```

**Python + Node** (caminho B):
```bash
brew install python@3.12 node@22
python3 --version
node --version
```

### Windows (10/11)

**Docker** (caminho A):
- Habilite o **WSL 2** (instruções: <https://learn.microsoft.com/windows/wsl/install>).
- Instale **Docker Desktop** com integração WSL 2: <https://www.docker.com/products/docker-desktop>.
- Abra o Docker Desktop uma vez e verifique no PowerShell ou WSL:
  ```powershell
  docker --version
  docker compose version
  ```
- Recomendado rodar o projeto **dentro do WSL** (clonando o repo em `~/projetos`
  dentro da distro Ubuntu, não em `C:\`) — performance de I/O é dramaticamente
  melhor.

**Python + Node** (caminho B):
- Python: instale do <https://www.python.org/downloads/>, marcando "Add to PATH".
- Node: instale do <https://nodejs.org/> (versão LTS).
- Reabra o PowerShell e teste: `python --version`, `node --version`.

---

## 4. Caminho A — Rodando via Docker (recomendado)

A partir da pasta `poc-app/`:

```bash
# 1. Copie o exemplo de variáveis de ambiente
cp .env.example .env
# Opcional: edite .env e mude JWT_SECRET para algo aleatório

# 2. Build + sobe os dois serviços
docker compose up --build

# (ou em segundo plano)
docker compose up --build -d
docker compose logs -f
```

A primeira vez demora alguns minutos (Node baixando dependências, imagens base).
Depois, subir/derrubar leva segundos.

**Acessos depois que subir:**

| URL                              | O que é                      |
| -------------------------------- | ---------------------------- |
| <http://localhost:8080>          | Frontend (Angular)           |
| <http://localhost:8000/docs>     | Backend (Swagger interativo) |
| <http://localhost:8000/api/health> | Health check               |

**Comandos úteis:**
```bash
docker compose down              # derruba os serviços
docker compose down -v           # derruba e apaga o volume do banco
docker compose logs -f backend   # acompanha logs de um serviço só
docker compose restart backend   # recarrega o backend (reseed automático)
docker compose ps                # status dos containers
```

---

## 5. Caminho B — Rodando em modo dev (sem Docker)

Útil para hot-reload e debugger. Vai precisar de **dois terminais**.

### Terminal 1 — backend

```bash
cd backend

# Cria e ativa virtualenv
python3 -m venv .venv
source .venv/bin/activate           # Linux/macOS
# .venv\Scripts\activate            # Windows PowerShell

pip install -r requirements.txt

# Roda em modo dev com auto-reload
DATABASE_URL=sqlite:///./app.db RESET_DB_ON_STARTUP=1 \
  uvicorn app.main:app --reload --port 8000
```

> No Windows PowerShell, em vez de `DATABASE_URL=... uvicorn ...`, use:
> ```powershell
> $env:DATABASE_URL="sqlite:///./app.db"
> $env:RESET_DB_ON_STARTUP="1"
> uvicorn app.main:app --reload --port 8000
> ```

Backend agora em <http://localhost:8000>.

### Terminal 2 — frontend

```bash
cd frontend

# Primeira vez:
npm install

# Sobe o dev server (auto-reload no save)
npm start
```

Frontend agora em <http://localhost:4200>.

> O `apiBaseUrl` em `src/environments/environment.ts` aponta para
> `http://localhost:8000` — combina com o backend rodando localmente.

---

## 6. Verificando que tudo funcionou

Independente do caminho escolhido, esse roteiro confirma as 5 user stories:

1. Abra <http://localhost:8080> (ou `:4200` no caminho B).
   Você deve cair em `/login`.
2. **US-02 — registro**: clique em "Cadastre-se", crie uma conta nova
   (ex.: nome `Teste`, e-mail `teste@example.com`, senha `Senha123`).
3. **US-01 — login**: faça login com `alice@example.com` / `Senha123`
   (ou com o usuário recém-criado).
4. **US-04 — lista e filtros**: você verá as solicitações da Alice. Mude o
   filtro de status / prioridade e veja a tabela atualizar. Selecione
   `cancelada` para ver o estado vazio com a mensagem "Nenhuma solicitação
   encontrada" (note: os filtros continuam visíveis).
5. **US-03 — criar**: clique em "+ Nova solicitação", preencha e envie.
   Você volta para a lista com a nova solicitação no topo.
6. **US-05 — cancelar**: numa solicitação `aberta` ou `em análise`, clique em
   "Cancelar". O dialog mostra o título da solicitação. Confirme.

---

## 7. Credenciais e dados de seed

O banco é **recriado em todo start** do backend (variável `RESET_DB_ON_STARTUP=1`).
Dois usuários sempre disponíveis, ambos com senha **`Senha123`**:

| E-mail                | Solicitações                                                  |
| --------------------- | ------------------------------------------------------------- |
| `alice@example.com`   | 4 solicitações cobrindo todos os status e três prioridades    |
| `bob@example.com`     | 2 solicitações (`aberta` alta, `em_analise` baixa)            |

> ⚠️ **Atenção**: o `smoke_test.py` deixa a Alice bloqueada (lockout 60s) ao
> terminar, então **se você acabou de rodar o smoke test, espere 1 minuto**
> antes de logar como alice, ou logue como bob.

Para desligar o reset e manter dados entre sessões, edite `.env`:
```
RESET_DB_ON_STARTUP=0
```

---

## 8. Endpoints da API

| Método | Path                                | História | Notas                                                              |
| ------ | ----------------------------------- | -------- | ------------------------------------------------------------------ |
| POST   | `/api/auth/register`                | US-02    | `name` 3-80, `email` válido, `password` ≥8 com letra+número        |
| POST   | `/api/auth/login`                   | US-01    | 401 genérico em falha; 423 + `Retry-After` após 5 falhas (60s)     |
| GET    | `/api/auth/me`                      | —        | Protegido; retorna o usuário do token                              |
| POST   | `/api/requests`                     | US-03    | Status `aberta` e data são definidos pelo servidor                 |
| GET    | `/api/requests`                     | US-04    | Query: `status`, `priority`; `scope=own` (default) ou `all`        |
| GET    | `/api/requests/{id}`                | —        | Usado pelo dialog de confirmação                                   |
| POST   | `/api/requests/{id}/cancel`         | US-05    | Só dono; só status em `{aberta, em_analise}`                       |

Os schemas exatos estão em `backend/app/schemas.py` e podem ser explorados
interativamente em <http://localhost:8000/docs>.

---

## 9. Smoke test (validação automática)

Roda os 17 casos que cobrem todas as regras das 5 user stories. Útil **sempre
que você mexer no backend** para garantir que nada quebrou:

```bash
cd backend
source .venv/bin/activate         # se não estiver ativo
python smoke_test.py
```

Saída esperada termina com `ALL SMOKE TESTS PASSED ✅`. Cobertura:

- US-01: login OK, mensagem genérica, sem enumeração, lockout de 60s
- US-02: cadastro OK, duplicidade rejeitada, complexidade de senha, tamanho do nome
- US-03: criação OK com status/data automáticos, validação de tamanhos e enum
- US-04: default só do próprio usuário ordenado por data, vazio é 200, filtros combinam
- US-05: ownership respeitada, transição de status, não cancela o que já foi cancelado

Esse script **não substitui** os PyTests gerados pelo pipeline na Fase 5 — ele é
só um cinto de segurança no contrato da API.

---

## 10. Troubleshooting

**“Port already in use”** (8000 ou 8080):
```bash
# Linux/macOS — descubra quem está usando:
lsof -i :8000
# Mate o processo OU mude o mapeamento no docker-compose.yml ("8001:8000")
```

**Docker build do frontend muito lento na primeira vez**: é o `npm install`
baixando ~850 pacotes. Builds subsequentes usam cache de layer e ficam ~10s.

**Erros de CORS no navegador**: o backend permite por padrão
`http://localhost:4200` e `http://localhost:8080`. Se acessar por outro host
(ex.: IP local), inclua na variável `CORS_ORIGINS` em `.env`:
```
CORS_ORIGINS=http://localhost:4200,http://localhost:8080,http://192.168.1.42:8080
```

**Backend health check falhando no Docker**: aguarde ~15s no primeiro start. Se
persistir:
```bash
docker compose logs backend
```

**"alice" não consegue logar**: provavelmente o smoke test rodou recentemente e
ela está em lockout. Espere 60s ou use `bob@example.com`.

**Build do Angular falha com “out of memory”**: aumente o heap do Node:
```bash
NODE_OPTIONS=--max-old-space-size=4096 npm run build:prod
```

**Quero apagar o banco e começar do zero**:
```bash
docker compose down -v       # remove o volume
docker compose up --build    # reseed acontece automaticamente
```

---

## ✅ Done-check da Fase 1 (do `plan.md` §5)

- [x] Backend FastAPI com endpoints para as 5 histórias e regras de negócio explícitas
- [x] Seed estável e reproduzível (reset em todo start)
- [x] Backend como serviço do `docker compose`
- [x] Frontend Angular com `data-testid` em todo elemento interativo desde o dia 1
- [x] Frontend como serviço do `docker compose`
- [x] Seletores documentados (`ui_map.json`)

Próximo: **Fase 2 — Context Builder** (a partir do `glossary.md` e do
`ui_map.json` que já temos aqui).
