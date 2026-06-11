# Guia para Agentes de IA - UFPB Chat System

Este arquivo e o **ponto de partida obrigatorio** para qualquer agente que for
modificar o projeto. Ele documenta a arquitetura, os parametros configuraveis,
os contratos de API, os fluxos de negocio e as armilhas conhecidas encontradas
durante a leitura completa do codigo.

---

## Sumario

1. [Resumo do Projeto](#1-resumo-do-projeto)
2. [Arquitetura](#2-arquitetura)
3. [Estrutura de Diretorios](#3-estrutura-de-diretorios)
4. [Inicializacao da Aplicacao](#4-inicializacao-da-aplicacao)
5. [Configuracao e Variaveis de Ambiente](#5-configuracao-e-variaveis-de-ambiente)
6. [Banco de Dados e Modelos](#6-banco-de-dados-e-modelos)
7. [Dependencias e Autorizacao](#7-dependencias-e-autorizacao)
8. [Rotas HTTP](#8-rotas-http)
9. [Servico de Mensagens e Webhooks](#9-servico-de-mensagens-e-webhooks)
10. [Frontend](#10-frontend)
11. [Scripts e Docker](#11-scripts-e-docker)
12. [Armilhas Conhecidas](#12-armilhas-conhecidas)
13. [Checklist para Novos Agentes](#13-checklist-para-novos-agentes)
14. [Mapa Rapido de Arquivos](#14-mapa-rapido-de-arquivos)

---

## 1. Resumo do Projeto

O projeto e uma aplicacao FastAPI para **atendimento multiatendente via WhatsApp**, com:

- Frontend estatico em `/inbox` (vanilla JS, sem build step)
- Banco PostgreSQL via SQLAlchemy
- Integracao com EvolutionAPI v2.3.7 / n8n para envio/recebimento de mensagens
- Upload de midia (imagens, audios, documentos)
- Templates de mensagens
- Exportacao de conversas (PDF com ReportLab, HTML)
- Recursos de IA (consulta via n8n, agente automatico)

**Stack:** Python 3.12 / FastAPI 0.128.3 / SQLAlchemy 2.0.40 / PostgreSQL / Vanilla JS  
**Container:** Docker (python:3.12-slim + FFmpeg)  
**Deploy:** EasyPanel  

### Pontos de Entrada Principais

| Arquivo | Funcao |
| --- | --- |
| `app/main.py` | Ponto de entrada - cria `app = create_application()` |
| `app/core/app_factory.py` | Factory Pattern - configura FastAPI, CORS, rotas, static files, lifespan |
| `app/core/config.py` | `Settings` (pydantic-settings) - todas as variaveis de ambiente |
| `app/services/messages.py` | CORE - ingestao de webhooks, normalizacao, envio outbound |
| `app/static/inbox/app.js` | Frontend vanilla JS (~3000 linhas) |
| `app/static/inbox/index.html` | HTML principal do frontend |
| `app/static/inbox/styles.css` | Estilos (~2800 linhas) |

### Comandos Uteis

```bash
# Verificacao de sintaxe
python -m compileall app scripts
node --check app/static/inbox/app.js

# Rodar localmente
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Docker
docker compose up -d --build
docker compose logs -f
```

---

## 2. Arquitetura

### Padroes de Projeto

- **Factory Pattern**: `app/core/app_factory.py` cria e configura o FastAPI
- **Singleton**: `RuntimeSettings` (id=1) com cache em memoria via `runtime_settings.py`
- **Challenge-Response**: login anti-bots com desafio temporario (`login_challenge.py`)
- **Clean Code**: separacao em `api/routes`, `services`, `models`, `schemas`, `utils`

### Ciclo de Vida da Aplicacao

`create_application()` instancia `ApplicationFactory`, que:

1. Carrega `get_settings()` do `.env`
2. Configura logging via `setup_logging()`
3. Cria `FastAPI(...)` com docs em `/api/v1/docs`
4. Configura CORS (via `Settings.cors_*`)
5. Registra middleware HTTP de logging detalhado
6. Monta static files:
   - `/inbox` -> `app/static/inbox` (com `html=True`)
   - `/uploads` -> `settings.media_storage_path`
7. Registra todas as rotas (webhook publico + API versionada)
8. Configura exception handlers globais
9. Lifespan de startup:
   - Aguarda banco (`SELECT 1` com retry, 30 tentativas)
   - `Base.metadata.create_all(bind=engine)` - cria tabelas
   - `ensure_schema_compatibility(engine)` - ADD COLUMN IF NOT EXISTS
   - `ensure_initial_admin_user(db)` - cria admin se nao existir
   - `get_or_create_runtime_settings(db)` - singleton
   - `_initialize_system_templates(db)` - templates LGPD/Pesquisa
   - `sync_webhook_urls_on_startup()` - env -> banco
   - `media_storage_path.mkdir()` - garante diretorio de midia

Ao acessar `/`, redireciona para `/inbox`.

### Fluxo de Mensagens

**Inbound (WhatsApp -> Sistema):**
1. EvolutionAPI envia payload para n8n
2. n8n encaminha para `/webhook` ou `/api/inbox`
3. `_validate_inbound_token()` valida token (env ou banco)
4. `ingest_inbound_message()`:
   - Normaliza telefone via `_normalize_phone()`
   - Detecta tipo via `_extract_type()`
   - Extrai midia de base64 ou baixa da CDN
   - Cria `Conversation` se nao existir
   - Cria `Message` com `direction=inbound`, `delivery_status=received`
   - Atualiza `conversation.last_message_at`
   - Opcionalmente encaminha para agente IA (background task)

**Outbound (Sistema -> WhatsApp):**
1. Atendente envia via frontend (POST `/conversations/{id}/messages`)
2. `create_outbound_message()`:
   - Cria `Message` com `direction=outbound`, `delivery_status=queued`
   - Atualiza `conversation.last_message_at` e `attendant.last_interaction_at`
   - Busca URL outbound efetiva (env > banco)
   - Monta payload para n8n (to, text, media, attendant)
   - Auth outbound (header/basic/jwt conforme configuracao)
   - POST com timeout 20s
   - Sucesso -> `delivery_status=SENT`
   - Erro -> `delivery_status=FAILED` + `error_message`

**Status Update (WhatsApp -> Sistema):**
1. EvolutionAPI envia `messages.update` com status
2. Normaliza status (string ou numerico)
3. Atualiza `delivery_status` da mensagem por `external_message_id`

**Edicao (WhatsApp -> Sistema):**
1. `messages.update` com `data.update.message.editedMessage` -> atualiza texto
2. `messages.upsert` com `secretEncryptedMessage` -> marca `is_edited=True`
3. Atendente edita -> PATCH `/conversations/{id}/messages/{id}/edit`

**Delete/Revoke (WhatsApp -> Sistema):**
1. `messages.delete` -> marca texto como "Essa mensagem foi apagada"
2. Atendente revoga -> POST `/conversations/{id}/messages/{id}/revoke` -> envia para n8n

---

## 3. Estrutura de Diretorios

```
chatZapUFPB/
├── app/
│   ├── api/
│   │   ├── deps.py                 # Dependencias FastAPI (auth, sessao)
│   │   └── routes/
│   │       ├── auth.py             # Login, logout, challenge-response
│   │       ├── users.py            # CRUD de usuarios (admin)
│   │       ├── conversations.py    # CRUD conversas, mensagens, edicao, export
│   │       ├── webhook.py          # Webhooks publicos (/webhook, /api/inbox)
│   │       ├── admin.py            # Config webhook/IA, cleanup
│   │       ├── templates.py        # CRUD de templates
│   │       ├── uploads_v2.py       # Upload de midia (ativo)
│   │       ├── uploads.py          # Upload legado (NAO registrado)
│   │       ├── whatsapp_tools.py   # Status de midia WhatsApp
│   │       ├── ai.py               # Consulta IA
│   │       └── health.py           # Health check
│   ├── core/
│   │   ├── config.py               # Settings (pydantic-settings)
│   │   ├── app_factory.py          # Factory Pattern
│   │   ├── exceptions.py           # Handlers de excecao
│   │   ├── logging.py              # Configuracao de logging
│   │   └── security.py             # Utilitarios genericos (NAO usado pelas rotas)
│   ├── db/
│   │   ├── base.py                 # Base declarativa SQLAlchemy
│   │   └── session.py              # Engine + SessionLocal
│   ├── models/
│   │   ├── user.py                 # Usuario
│   │   ├── conversation.py         # Conversa
│   │   ├── message.py              # Mensagem (enums: Direction, Type, Status)
│   │   ├── runtime_settings.py     # Singleton de configuracao
│   │   └── template.py             # Template de mensagens
│   ├── schemas/                    # Modelos Pydantic para API
│   ├── services/
│   │   ├── messages.py             # CORE - ingestao, normalizacao, envio
│   │   ├── bootstrap.py            # Admin inicial
│   │   ├── login_challenge.py      # Challenge-response
│   │   ├── runtime_settings.py     # Cache de RuntimeSettings
│   │   ├── schema_maintenance.py   # ALTER TABLEs (ADD COLUMN IF NOT EXISTS)
│   │   ├── conversation_export.py  # Geracao PDF/HTML
│   │   ├── template_service.py     # CRUD de templates
│   │   ├── webhook_sync.py         # Sync env -> banco
│   │   ├── webhook_utils.py        # Token de webhook
│   │   └── media/
│   │       └── media_service.py    # Upload, validacao, delete
│   ├── static/inbox/               # Frontend vanilla JS
│   └── utils/
│       └── security.py             # JWT, hash (USADO pelas rotas atuais)
├── scripts/                        # Scripts de diagnostico e suporte
├── Dockerfile                      # Python 3.12 + FFmpeg
├── docker-compose.yml              # Compose para EasyPanel
├── requirements.txt                # Dependencias PyPI
├── .env.example                    # Template de variaveis
├── AGENTS.md                       # Este arquivo
└── README.md                       # Documentacao geral
```

---

## 4. Inicializacao da Aplicacao

### Startup Sequence (app_factory.py:279-342)

```
1. _wait_for_database()           # SELECT 1 com retry (30x, 2s intervalo)
2. Base.metadata.create_all()     # Cria tabelas se nao existirem
3. ensure_schema_compatibility()  # ADD COLUMN IF NOT EXISTS para todos os campos novos
4. ensure_initial_admin_user()    # Cria admin se tabela vazia
5. get_or_create_runtime_settings() # Singleton id=1
6. _initialize_system_templates() # LGPD + Pesquisa se nao existirem
7. sync_webhook_urls_on_startup() # Sincroniza URLs de env para o banco
8. media_storage_path.mkdir()     # Garante diretorio de uploads
```

### Schema Migration (schema_maintenance.py)

Nao usa Alembic. Em vez disso, roda `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para cada campo novo. Isso e seguro para rodar repetidamente.

Campos migrados:
- `users`: `last_login_at`, `last_logout_at`, `last_interaction_at`
- `runtime_settings`: `outbound_auth_*`, `ai_provider`, `ai_api_key`, `ai_base_url`, `ai_model`
- `conversations`: `profile_picture_url`
- `messages`: `updated_at`, `is_edited`, `is_read`, `quoted_message_text`, `quoted_message_sender`

---

## 5. Configuracao e Variaveis de Ambiente

Todas as configuracoes vivem em `app/core/config.py`. O `Settings` usa `pydantic-settings`, le `.env`, ignora campos extras (`extra="ignore"`) e e case-insensitive.

### Aplicacao

| Variavel | Campo | Tipo/Default | Efeito |
| --- | --- | --- | --- |
| `APP_NAME` | `app_name` | `str`, `UFPB Chat Multiatendente` | Nome nos metadados FastAPI |
| `APP_VERSION` | `app_version` | `str`, `2.0.0` | Versao logica |
| `API_V1_PREFIX` | `api_v1_prefix` | `str`, `/api/v1` | Prefixo das rotas |
| `ENVIRONMENT` | `environment` | `development\|production\|testing` | Controla logging |
| `DEBUG` | `debug` | `bool`, `False` | Exposto em `/auth/config` |
| `LOG_LEVEL` | `log_level` | `str`, `INFO` | Nivel de log |

### Banco de Dados

| Variavel | Campo | Tipo/Default | Efeito |
| --- | --- | --- | --- |
| `DATABASE_URL` | `database_url` | `str` | URL de conexao PostgreSQL |
| `DATABASE_POOL_SIZE` | `database_pool_size` | `int`, `5` | Declarado, nao usado atualmente |
| `DATABASE_MAX_OVERFLOW` | `database_max_overflow` | `int`, `10` | Declarado, nao usado |
| `DATABASE_POOL_TIMEOUT` | `database_pool_timeout` | `int`, `30` | Declarado, nao usado |

`app/db/session.py` cria `engine = create_engine(settings.database_url, pool_pre_ping=True)`.

### Seguranca

| Variavel | Campo | Tipo/Default | Efeito |
| --- | --- | --- | --- |
| `SECRET_KEY` | `secret_key` | `str`, `change-me-in-production` | Assina JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `access_token_expire_minutes` | `int`, `43200` (30 dias) | Validade do token |
| `PASSWORD_MIN_LENGTH` | `password_min_length` | `int`, `8` | Usado por `validate_password_strength` |

**ATENCAO:** Existem DOIS modulos de seguranca:
- `app/utils/security.py` - USADO pelas rotas atuais (hash_password, verify_password, create_access_token, decode_access_token)
- `app/core/security.py` - Utilitarios genericos, parcialmente nao usados

Nao misture as duas APIs sem revisar o formato do JWT.

### Admin Inicial

| Variavel | Campo | Tipo/Default | Efeito |
| --- | --- | --- | --- |
| `ADMIN_NAME` | `admin_name` | `str`, `Admin Principal` | Nome do admin |
| `ADMIN_EMAIL` | `admin_email` | `str`, `admin@example.com` | Email unico |
| `ADMIN_BOOTSTRAP_FILE` | `admin_bootstrap_file` | `Path`, `/app/runtime/admin_bootstrap.txt` | Arquivo com senha gerada |

`ADMIN_PASSWORD` aparece no README mas NAO existe em `Settings` e NAO e usado. O admin recebe senha aleatoria em `ensure_initial_admin_user()`.

### Webhooks

| Variavel | Campo | Tipo/Default | Efeito |
| --- | --- | --- | --- |
| `WEBHOOK_TOKEN` | `webhook_token` | `str\|None` | Token inbound |
| `N8N_WEBHOOK_MODE` | `n8n_webhook_mode` | `test\|prod`, `prod` | Seleciona URLs |
| `N8N_INBOUND_WEBHOOK_URL_TEST` | `n8n_inbound_webhook_url_test` | URL opcional | URL inbound (test) |
| `N8N_INBOUND_WEBHOOK_URL_PROD` | `n8n_inbound_webhook_url_prod` | URL opcional | URL inbound (prod) |
| `N8N_OUTBOUND_WEBHOOK_URL_TEST` | `n8n_outbound_webhook_url_test` | URL opcional | URL outbound (test) |
| `N8N_OUTBOUND_WEBHOOK_URL_PROD` | `n8n_outbound_webhook_url_prod` | URL opcional | URL outbound (prod) |
| `N8N_OUTBOUND_AUTH_TYPE` | `n8n_outbound_auth_type` | `none\|header\|basic\|jwt` | Tipo de auth outbound |

**IMPORTANTE:** `N8N_INBOUND_WEBHOOK_URL` e `N8N_OUTBOUND_WEBHOOK_URL` (sem `_TEST`/`_PROD`) NAO sao campos reais e sao ignorados por `extra="ignore"`.

Propriedades computadas (config.py:150-160):
- `n8n_inbound_webhook_url` -> retorna `_test` ou `_prod` conforme `n8n_webhook_mode`
- `n8n_outbound_webhook_url` -> retorna `_test` ou `_prod` conforme `n8n_webhook_mode`
- `ai_agent_webhook_url` -> retorna `_test` ou `_prod` conforme `ai_webhook_mode`

### Midia

| Variavel | Campo | Tipo/Default | Efeito |
| --- | --- | --- | --- |
| `UPLOADS_DIR` | `media_storage_path` | `Path`, `/opt/projetos/chatZapUFPB/uploads` | Diretorio de uploads (via env) |
| `MEDIA_MAX_FILE_SIZE` | `media_max_file_size` | `int`, 25MB | Limite por arquivo |
| `MEDIA_ALLOWED_EXTENSIONS` | `media_allowed_extensions` | lista | Extensao aceitas |

### IA

| Variavel | Campo | Tipo/Default | Efeito |
| --- | --- | --- | --- |
| `AI_WEBHOOK_MODE` | `ai_webhook_mode` | `test\|prod`, `prod` | Modo IA |
| `AI_WEBHOOK_URL_TEST` | `ai_webhook_url_test` | URL opcional | Webhook IA (test) |
| `AI_WEBHOOK_URL_PROD` | `ai_webhook_url_prod` | URL opcional | Webhook IA (prod) |
| `AI_AGENT_WEBHOOK_URL_TEST` | `ai_agent_webhook_url_test` | URL opcional | Agente automatico (test) |
| `AI_AGENT_WEBHOOK_URL_PROD` | `ai_agent_webhook_url_prod` | URL opcional | Agente automatico (prod) |
| `AI_WEBHOOK_USERNAME` | `ai_webhook_username` | `str\|None` | Basic Auth IA |
| `AI_WEBHOOK_PASSWORD` | `ai_webhook_password` | `str\|None` | Basic Auth IA |
| `OLLAMA_BASE_URL` | `ollama_base_url` | `str` | URL Ollama |

### CORS e Externos

| Variavel | Campo | Tipo/Default | Efeito |
| --- | --- | --- | --- |
| `CORS_ORIGINS` | `cors_origins` | `str`, `*` | Dominios permitidos (virgula) |
| `PUBLIC_DOMAIN` | `public_domain` | `str\|None` | Dominio para URLs absolutas |

---

## 6. Banco de Dados e Modelos

### users (app/models/user.py)

| Campo | Tipo | Constraints | Descricao |
| --- | --- | --- | --- |
| `id` | Integer | PK | ID unico |
| `name` | String(120) | NOT NULL | Nome |
| `email` | String(255) | UNIQUE, NOT NULL | Email |
| `password_hash` | String(255) | NOT NULL | Hash bcrypt |
| `must_change_password` | Boolean | NOT NULL, default True | Bloqueia ate trocar senha |
| `is_admin` | Boolean | NOT NULL, default False | Acesso admin |
| `is_active` | Boolean | NOT NULL, default True | Ativo/inativo |
| `last_login_at` | TIMESTAMPTZ | nullable | Ultimo login |
| `last_logout_at` | TIMESTAMPTZ | nullable | Ultimo logout |
| `last_interaction_at` | TIMESTAMPTZ | nullable | Para expirar sessao (7 dias) |
| `created_at` | TIMESTAMPTZ | NOT NULL | Criacao |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Atualizacao |

Relacao: `outbound_messages` com `Message.attendant`.

### conversations (app/models/conversation.py)

| Campo | Tipo | Constraints | Descricao |
| --- | --- | --- | --- |
| `id` | Integer | PK | ID unico |
| `contact_phone` | String(30) | UNIQUE, NOT NULL | Telefone normalizado `+<digitos>` |
| `contact_name` | String(120) | nullable | Nome do contato |
| `profile_picture_url` | String(1000) | nullable | URL da foto |
| `created_at` | TIMESTAMPTZ | NOT NULL | Criacao |
| `last_message_at` | TIMESTAMPTZ | NOT NULL | Para ordenar inbox |

Relacao: `messages` com cascade `all, delete-orphan`.

### messages (app/models/message.py)

**Enums:**

- `MessageDirection`: `inbound`, `outbound`
- `MessageType`: `text`, `image`, `audio`, `video`, `document`
- `DeliveryStatus`: `received`, `queued`, `sent`, `delivered`, `read`, `failed`

| Campo | Tipo | Constraints | Descricao |
| --- | --- | --- | --- |
| `id` | Integer | PK | ID unico |
| `conversation_id` | Integer | FK conversations, NOT NULL | Conversa |
| `direction` | Enum | NOT NULL | inbound/outbound |
| `message_type` | Enum | NOT NULL | text/image/audio/video/document |
| `delivery_status` | Enum | NOT NULL | Status atual |
| `text_content` | Text | nullable | Conteudo textual |
| `media_url` | Text | nullable | URL local `/uploads/...` ou externa |
| `media_mime_type` | String(150) | nullable | MIME type |
| `media_caption` | Text | nullable | Legenda |
| `sender_name` | String(120) | nullable | Nome do remetente |
| `sender_phone` | String(30) | nullable | Telefone do remetente |
| `attendant_id` | Integer | FK users, nullable | Atendente (outbound) |
| `external_message_id` | String(150) | nullable, index | ID WhatsApp/Evolution |
| `raw_payload` | JSON | nullable | Payload original |
| `error_message` | Text | nullable | Erro de envio |
| `created_at` | TIMESTAMPTZ | NOT NULL | Criacao |
| `updated_at` | TIMESTAMPTZ | nullable | Atualizacao |
| `is_edited` | Boolean | NOT NULL, default False | Mensagem editada |
| `is_read` | Boolean | NOT NULL, default False | Mensagem lida |
| `quoted_message_text` | Text | nullable | Texto da mensagem citada |
| `quoted_message_sender` | String(120) | nullable | Remetente da mensagem citada |

### runtime_settings (app/models/runtime_settings.py)

Singleton com `id=1`:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `outbound_webhook_url` | String(1000) | URL outbound |
| `outbound_auth_type` | String(20) | none/header/basic/jwt |
| `outbound_auth_header_name` | String(100) | Nome do header |
| `outbound_auth_header_value` | String(1000) | Valor do header |
| `outbound_auth_basic_username` | String(255) | Usuario Basic |
| `outbound_auth_basic_password` | String(1000) | Senha Basic |
| `outbound_auth_jwt_token` | String(2000) | Token JWT |
| `inbound_webhook_token` | String(255) | Token inbound |
| `ai_agent_enabled` | Boolean | Agente IA ligado |
| `ai_provider` | String(50) | gemini/openai/groq/ollama |
| `ai_api_key` | String(500) | Chave da API |
| `ai_base_url` | String(500) | URL base |
| `ai_model` | String(100) | Modelo |

`app/services/runtime_settings.py` mantem cache em memoria. SEMPRE chame `invalidate_runtime_cache()` depois de escrita.

### message_templates (app/models/template.py)

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `id` | Integer | PK |
| `title` | String(200) | Titulo |
| `content` | Text | Conteudo |
| `category` | String(50) | Categoria |
| `is_active` | Boolean | Ativo |
| `is_system` | Boolean | Template de sistema |
| `created_by` | Integer | ID do criador |

Templates de sistema sao criados no startup (LGPD + Pesquisa).

---

## 7. Dependencias e Autorizacao

### Arquivo: app/api/deps.py

- `oauth2_scheme`: espera `Authorization: Bearer <token>`
- `get_current_user(db, token)`:
  - Decodifica JWT com `app/utils/security.py`
  - Exige `sub` numerico
  - Usuario ativo
  - Sessao sem mais de 7 dias de inatividade
- `get_current_user_password_changed(current_user)`: bloqueia se `must_change_password=True`
- `get_current_admin(current_user)`: exige `is_admin=True`

**Hierarquia de dependencias:**
```
get_current_user -> get_current_user_password_changed -> get_current_admin
```

Use a mais restritiva compativel com o endpoint.

---

## 8. Rotas HTTP

### Auth (app/api/routes/auth.py, prefixo `/auth`)

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/auth/challenge` | Publico | Desafio anti-bots (expira 120s) |
| `POST` | `/auth/login` | Publico | Login com challenge |
| `GET` | `/auth/me` | JWT | Dados do usuario |
| `GET` | `/auth/config` | Publico | public_domain, environment, debug |
| `POST` | `/auth/change-password` | JWT | Troca de senha |
| `POST` | `/auth/logout` | JWT | Logout |

### Users (app/api/routes/users.py, prefixo `/users`)

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/users?active_only=true` | Admin | Lista usuarios |
| `POST` | `/users` | Admin | Cria usuario (must_change_password=True) |
| `POST` | `/users/{id}/reset-password` | Admin | Reseta senha |
| `PATCH` | `/users/{id}/status` | Admin | Ativa/desativa |
| `DELETE` | `/users/{id}` | Admin | Remove (nao admin a si mesmo) |

### Conversations (app/api/routes/conversations.py, prefixo `/conversations`)

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/conversations` | JWT | Lista conversas com mensagens |
| `POST` | `/conversations` | JWT | Cria conversa manual |
| `GET` | `/conversations/contacts/all` | JWT | Todos os contatos |
| `GET` | `/conversations/search/messages?q=` | JWT | Busca em mensagens (min 3 chars) |
| `GET` | `/conversations/{id}/messages` | JWT | Lista mensagens |
| `POST` | `/conversations/{id}/messages` | JWT | Envia mensagem outbound |
| `PATCH` | `/conversations/{id}/messages/{id}/edit` | JWT | Edita mensagem outbound |
| `POST` | `/conversations/{id}/messages/{id}/revoke` | JWT | Revoga mensagem |
| `POST` | `/conversations/{id}/messages/read` | JWT | Marca como lida |
| `POST` | `/conversations/{id}/messages/delete-selected` | Admin | Delete em lote |
| `DELETE` | `/conversations/{id}/messages/all` | Admin | Apaga todas da conversa |
| `DELETE` | `/conversations/messages/all` | Admin | Apaga tudo |
| `GET` | `/conversations/{id}/export` | JWT | Export JSON |
| `GET` | `/conversations/{id}/export/pdf` | JWT | Export PDF |

### Webhooks (app/api/routes/webhook.py)

**Rotas versionadas:**
- `POST /api/v1/webhooks/evolution`

**Rotas publicas (sem prefixo /api/v1):**
- `POST /webhook`
- `POST /api/inbox`

Headers para token: `x-webhook-token`, `x-token`, `Authorization: Bearer`, query `?token=`

Todas chamam `_handle_webhook_payload()` que:
1. Valida token
2. Chama `ingest_inbound_message()`
3. Agenda `_forward_to_ai_agent()` em background

### Admin (app/api/routes/admin.py, prefixo `/admin`)

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/admin/webhook-settings` | Admin | Config webhooks |
| `PUT` | `/admin/webhook-settings` | Admin | Atualiza webhooks |
| `GET` | `/admin/ai-settings` | Admin | Config IA |
| `PUT` | `/admin/ai-settings` | Admin | Atualiza IA |
| `DELETE` | `/admin/cleanup/messages` | Admin | Apaga todas mensagens |
| `DELETE` | `/admin/cleanup/uploads` | Admin | Apaga todas midias |
| `DELETE` | `/admin/cleanup/contacts` | Admin | Apaga todas conversas |

### Templates (app/api/routes/templates.py, prefixo `/templates`)

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/templates` | JWT | Lista templates |
| `GET` | `/templates/{id}` | JWT | Template especifico |
| `POST` | `/templates` | Admin | Cria template |
| `PUT` | `/templates/{id}` | Admin | Atualiza template |
| `DELETE` | `/templates/{id}` | Admin | Remove template |
| `GET` | `/templates/category/{category}` | JWT | Por categoria |
| `POST` | `/templates/initialize` | Admin | Cria LGPD/Pesquisa |

### Uploads (app/api/routes/uploads_v2.py, prefixo `/uploads`)

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `POST` | `/uploads/media` | JWT | Upload (rejeita video) |
| `GET` | `/uploads/media/{filename}` | JWT | Info do arquivo |
| `DELETE` | `/uploads/media/{filename}` | JWT | Remove arquivo |
| `POST` | `/uploads/cleanup?days=30` | Admin | Limpa arquivos antigos |

### IA (app/api/routes/ai.py, prefixo `/ai`)

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `POST` | `/ai/ask` | JWT | Pergunta para IA |
| `GET` | `/ai/fetch-models?provider=` | JWT | Lista modelos |

### Health (app/api/routes/health.py)

- `GET /health` - retorna `{"status": "ok"}`
- `GET /health/integrations` - mostra URLs/mode de webhooks

---

## 9. Servico de Mensagens e Webhooks

### Arquivo: app/services/messages.py (~1350 linhas)

Este e o coracao do sistema. Contem toda a logica de ingestao, normalizacao e envio.

### Funcoes Principais

#### `_normalize_phone(raw) -> str | None`
- Remove tudo que nao for digito
- Adiciona `55` para telefones BR de 10/11 digitos
- Remove 9o digito para DDD > 28 (regra JID WhatsApp)
- Retorna `+<digitos>` ou `None`

#### `_extract_type(raw_type, has_media, message) -> MessageType`
Detecta tipo da mensagem por:
1. `raw_type` (string com "document", "image", "audio", "video")
2. Chaves no `message` (documentMessage, imageMessage, etc.)
3. Fallback para TEXT

#### `_download_whatsapp_media(data, message_id, instance, message_type, mime_type)`
- Prioriza base64 em `data.message.base64` (ou `data.base64`)
- Fallback: download da CDN via EvolutionAPI
- Salva em `settings.media_storage_path`
- Retorna `/uploads/<filename>`
- Suporta dict com chaves numericas e string base64

#### `_download_profile_picture(payload, contact_phone)`
- Busca URL da foto no payload ou via EvolutionAPI
- Salva localmente com prefixo `profile_`
- Retorna `/uploads/<filename>`

#### `normalize_webhook_payload(payload) -> dict`
Normaliza payload bruto em evento estruturado:
- `event`: tipo do evento (messages.upsert, messages.update, contacts.upsert, etc.)
- `contact_phone`: telefone normalizado
- `contact_name`: nome do contato
- `message_type`: MessageType
- `text_content`: texto
- `media_url`: URL local
- `media_mime_type`: MIME
- `sender`: remetente
- `direction`: inbound/outbound
- `key_id`: ID da mensagem
- `status`: DeliveryStatus (para updates)
- `delivery_status`: mapeado de string/numero

**Eventos suportados:**
- `contacts.upsert` / `contacts.update` - atualizacao de contato
- `messages.upsert` - nova mensagem (inclui `secretEncryptedMessage`, `editedMessage`)
- `messages.update` - atualizacao de status ou edicao
- `messages.delete` - marcacao como apagada
- `messages.edited` - futuro (EvolutionAPI v2.3.7 nao tem)

#### `ingest_inbound_message(db, payload) -> Message | Conversation | None`
1. Chama `normalize_webhook_payload()`
2. Rejeita sem telefone
3. Ignora `contact_phone == "+558332167336"` (bot)
4. Ignora `contact_phone == sender` (auto-mensagem)
5. `messages.update` -> atualiza status
6. `messages.delete` -> marca apagada
7. Cria ou atualiza `Conversation`
8. Atualiza `profile_picture_url`
9. `contacts.upsert` -> retorna conversa sem criar mensagem
10. Evita duplicata por `external_message_id`
11. Outbound recente sem `external_id` -> tenta casar por texto
12. Cria `Message`

#### `create_outbound_message(db, conversation, attendant, data) -> Message`
1. Cria `Message` OUTBOUND com QUEUED
2. Atualiza `conversation.last_message_at` e `attendant.last_interaction_at`
3. Busca URL outbound (env > banco)
4. Monta payload para n8n
5. Auth conforme configuracao
6. POST timeout 20s
7. Sucesso -> SENT, erro -> FAILED

### Deteccao de Edicao

**messages.update (EvolutionAPI v2.3.7):**
```
data.update.message.editedMessage.message.conversation  # caminho primario
data.update.message.editedMessage.conversation           # fallback
data.message.conversation                                # fallback
```
Procura texto recursivamente nas chaves do dict.

**messages.upsert com secretEncryptedMessage:**
- Detecta `data.get("messageType") == "secretEncryptedMessage"`
- Extrai `targetMessageKey.id` para encontrar mensagem original
- Marca `is_edited=True`, nao cria duplicata

**messages.upsert com editedMessage:**
- Detecta `data.message.editedMessage` ou `data.editedMessage`
- Retorna como evento `messages.edited`

### Deduplicacao

- Por `external_message_id`: evita duplicatas diretas
- Por texto + janela de 2 minutos: evita duplicatas de outbound sem ID
- Comparacao Python (nao SQL) para lidar com `NULL = NULL` (retorna NULL, nao TRUE)

### Status Mapping

| EvolutionAPI | Sistema | Observacao |
| --- | --- | --- |
| `SERVER_ACK`, `"1"` | `SENT` | Servidor recebeu |
| `DELIVERY_ACK`, `"2"` | `DELIVERED` | Entregue ao dispositivo |
| `PLAYED`, `"3"` | `READ` | Audio reproduzido |
| `READ`, `"4"` | `READ` | Visualizado |
| `ERROR`, `"5"` | `FAILED` | Falha no envio |
| `SENDING`, `"6"` | `QUEUED` | Em fila |
| `PROGRESS`, `"7"` | `SENT` | Em progresso |

Mapping usa string-first: tenta `status_string_map` antes de `int()` com try/except.

---

## 10. Frontend

### Arquivos

- `app/static/inbox/index.html` - HTML principal
- `app/static/inbox/app.js` - Logica (~3000 linhas)
- `app/static/inbox/styles.css` - Estilos (~2800 linhas)
- `app/static/inbox/img/` - Logos (brasao.png, sti_logo.png)

### Estado Global (app.js)

| Variavel | Descricao |
| --- | --- |
| `state.token` | JWT no localStorage (`ufpb_token`) |
| `state.user` | Usuario logado |
| `state.conversations` | Conversas da sidebar |
| `state.messagesByConversation` | Cache por conversa |
| `state.selectedConversationId` | Conversa ativa |
| `state.messagePollTimer` | Polling de mensagens (2s) |
| `state.conversationPollTimer` | Polling de conversas (5s) |
| `state.messageOffsets` / `state.hasMoreMessages` | Scroll infinito |
| `state.audioContext` / `state.analyser` | Gravacao de audio |
| `state.messageTemplates` | Templates carregados |
| `state.publicConfig` | Resposta de `/auth/config` |

### Objeto `els`

Mapeamento de IDs do HTML para variaveis JS. Grupos sensiveis:

- Login: `loginOverlay`, `loginForm`, `loginEmail`, `loginPassword`, `challengeQuestion`, `challengeAnswer`
- Senha: `passwordOverlay`, `passwordForm`, `currentPassword`, `newPassword`
- Chat: `conversationList`, `chatTitle`, `chatSubtitle`, `messageCountBadge`, `messages`
- Composer: `messageType`, `textContent`, `mediaUrl`, `mediaCaption`, `imageFileInput`, `sendMessageBtn`
- Templates: `templatesOverlay`, `templatesList`
- Export: `exportOverlay`, `exportDate`, `exportStartTime`, `exportEndTime`
- IA: `aiConsultOverlay`, `aiQuestion`, `aiResponse`, `configAiProvider`, `configAiAgentEnabled`

### Funcionalidades

- **Login com challenge-response**
- **Sidebar** ordenada por `last_message_at`
- **Chat** com mensagens (texto, imagem, audio, documento)
- **Composer** com upload, gravacao audio, templates (trigger `/`)
- **Edicao inline** - botao em mensagens outbound de texto
- **Revogacao** - botao de apagar
- **Mensagens nao lidas** - indicador visual
- **Citacao** - visualizacao de mensagem respondida
- **Modal de midia** - clique em imagem abre em tamanho completo
- **Preview de arquivo** - thumbnail apos upload
- **Templates** - modal de selecao
- **Exportacao** - PDF e HTML
- **Config IA** - toggle e selecao de provider

### Scroll Preservation

`renderMessages()` verifica `wasAtBottom` antes de substituir `innerHTML`. So faz scroll to bottom se o usuario ja estava no fundo ou se e o primeiro render.

### buildMessageBody()

Gera HTML interno da mensagem:
- `.message-quote` para mensagens citadas
- `<img>` para imagens com `openMediaModal()`
- `<video>` para videos com controles
- `<audio>` para audios
- `<a>` para documentos
- `.message-edited` para mensagens editadas
- Texto com `formatWhatsAppText()` (negrito, italico, tachado, codigo)

---

## 11. Scripts e Docker

### Dockerfile

- Base: `python:3.12-slim`
- Instala FFmpeg
- Copia `app/` e `scripts/`
- Cria `/opt/projetos/chatZapUFPB/uploads`, `/app/runtime`, `/app/logs`
- Healthcheck via HTTP em `/health`
- CMD: `startup_check.py` + uvicorn

### docker-compose.yml

```yaml
services:
  automacoes_sti_ufpb_whatsapp_fastapi:
    build: .
    env_file: .env
    ports: ["8000:8000"]
    volumes:
      - ./uploads:/opt/projetos/chatZapUFPB/uploads    # MIDIA
      - ./runtime:/app/runtime                          # Bootstrap
      - ./logs:/app/logs                                # Logs
    healthcheck: ...
```

### Docker Volumes - Explicacao Detalhada

**Como funciona um volume Docker:**
Um volume e uma ponte entre uma pasta do servidor (host) e uma pasta dentro do container.

**No docker-compose.yml:**
```yaml
volumes:
  - ./uploads:/opt/projetos/chatZapUFPB/uploads
```

Isso significa: "monte a pasta `uploads` do host dentro do container em `/opt/projetos/chatZapUFPB/uploads`".

**No EasyPanel:**
O caminho fisico real NO SERVIDOR nao e `./uploads`, mas sim:
```
/etc/easypanel/projects/automations-01/whatsapp_fastapi/volumes/uploads
```

Essa pasta e montada dentro do container em `/opt/projetos/chatZapUFPB/uploads`.

**Fluxo completo:**
```
Servidor (host)                                    Container
─────────────────────────────────────────────────────────────
/etc/easypanel/projects/.../uploads  ──mount──>  /opt/projetos/chatZapUFPB/uploads
```

**Por que `/uploads` nao existe:**
Ao tentar acessar `/uploads` dentro do container, ocorre "No such file or directory". O caminho correto e `/opt/projetos/chatZapUFPB/uploads`.

**Persistencia:**
Qualquer arquivo gravado nessa pasta dentro do container e armazenado fisicamente na pasta correspondente do servidor, permitindo que os dados permanecam mesmo que o container seja recriado.

### scripts/startup_check.py

Executado no CMD do Dockerfile:
1. Verifica FFmpeg (opcional - nao falha se faltar)
2. Verifica diretorios (`/opt/projetos/chatZapUFPB/uploads`, `/app/runtime`, `/app/logs`)
3. Testa permissoes de escrita

### Outros Scripts

- `verify_dependencies.py` - Diagnostico completo (FFmpeg, FFprobe, pacotes)
- `check_ffmpeg.py` - Teste detalhado de FFmpeg
- `test_webhook.py` - POST manual para `/api/inbox`
- `debug_download.py` - Teste de download base64
- `migrate_enum.py` - Migracao de enums PostgreSQL
- `init_templates.py` - Templates LGPD/Pesquisa

---

## 12. Armilhas Conhecidas

### Configuracao

1. **`N8N_INBOUND_WEBHOOK_URL` e `N8N_OUTBOUND_WEBHOOK_URL`** (sem `_TEST`/`_PROD`) NAO sao campos reais do `Settings` e sao ignorados por `extra="ignore"`. Use os campos `_TEST`/`_PROD`.

2. **`ADMIN_PASSWORD`** aparece no README mas NAO existe em `Settings`. O admin recebe senha aleatoria.

3. **Duas APIs de seguranca**: `app/utils/security.py` (usada pelas rotas) e `app/core/security.py` (genericas). Nao misture.

4. **`RuntimeSettings`** e um singleton cacheado. Para escrita, carregue na sessao atual e chame `invalidate_runtime_cache()` apos commit.

### Codigo

5. **Numero hardcoded** `+558332167336` em `app/services/messages.py` - ajuste se mudar o numero do bot.

6. **`uploads.py`** e rota legada nao registrada - use `uploads_v2.py`.

7. **`MediaService.get_media_info()`** referencia `video_converter` nao importado - caminho so e atingido com video no storage.

8. **`escapeHtml`** declarado duas vezes em `app.js` - a segunda sobrescreve a primeira.

9. **`recordPreview`** referenciado em `app.js` mas nao existe no `index.html` - pode quebrar ao abrir gravacao.

10. **`styles.css`** tem bloco de IA duplicado e trecho com `transform: scale(1)` solto dentro de `@media`.

11. **CSS brace mismatch** pre-existente por volta da linha 2788 em `styles.css` (documentado, nao corrigido).

### Infra

12. **`docker-compose.production.yml`** e `scripts/deploy.sh` esperam arquivos que nao existem.

13. **`init.sql`** contem apenas comentario deprecado - bootstrap agora e feito pelo app.

---

## 13. Checklist para Novos Agentes

### Antes de Alterar

- [ ] Leia este arquivo (AGENTS.md) e o modulo exato que vai tocar
- [ ] Rode `git status --short` e preserve alteracoes locais nao suas
- [ ] Confirme se a rota/servico que vai editar esta registrado em `ApplicationFactory`
- [ ] Se mexer em env, atualize `Settings`, `.env.example` e documentacao juntos
- [ ] Se mexer em modelo, revise schema Pydantic, rotas, frontend e `schema_maintenance.py`
- [ ] Se mexer no HTML, revise todas as chaves em `els` do `app.js`
- [ ] Se mexer no fluxo de mensagens, teste inbound, outbound, update, delete/revoke e deduplicacao

### Depois de Alterar

- [ ] Rode `python -m compileall app scripts`
- [ ] Rode `node --check app/static/inbox/app.js` se o JS mudou
- [ ] Se possivel, suba a aplicacao e teste:
  - [ ] `/health`
  - [ ] `/api/v1/docs`
  - [ ] Login com challenge
  - [ ] Listagem de conversas
  - [ ] Envio de mensagem
  - [ ] Upload de midia
  - [ ] Webhook inbound com token
  - [ ] Telas admin se afetar

### Regras de Codigo

- Nao adicione comentarios ou docstrings exceto se pedido explicitamente
- Mantenha a style existente (Python: 4 espacos, JS: 2 espacos)
- Nao assuma bibliotecas disponiveis - verifique `requirements.txt`
- Nao commite secrets ou chaves
- Use `get_settings()` para acessar configuracao (nao `os.getenv` direto)
- Para escrever no banco, sempre use a sessao da requisicao (nunca crie sessao manualmente em rotas)

---

## 14. Mapa Rapido de Arquivos

### Auth e Usuarios
- `app/api/routes/auth.py`
- `app/api/routes/users.py`
- `app/api/deps.py`
- `app/utils/security.py`
- `app/services/login_challenge.py`
- `app/services/bootstrap.py`

### Conversas e Mensagens
- `app/api/routes/conversations.py`
- `app/api/routes/webhook.py`
- `app/services/messages.py`
- `app/services/conversation_export.py`
- `app/models/conversation.py`
- `app/models/message.py`
- `app/schemas/conversation.py`
- `app/schemas/message.py`

### Admin/Settings
- `app/api/routes/admin.py`
- `app/models/runtime_settings.py`
- `app/schemas/admin.py`
- `app/services/runtime_settings.py`
- `app/services/webhook_utils.py`
- `app/services/webhook_sync.py`

### Templates
- `app/api/routes/templates.py`
- `app/models/template.py`
- `app/schemas/template.py`
- `app/services/template_service.py`

### Midia
- `app/api/routes/uploads_v2.py`
- `app/api/routes/whatsapp_tools.py`
- `app/services/media/media_service.py`
- `app/schemas/upload.py`

### IA
- `app/api/routes/ai.py`
- `app/schemas/ai.py`
- `app/schemas/admin.py`
- `app/services/runtime_settings.py`

### Frontend
- `app/static/inbox/index.html`
- `app/static/inbox/app.js`
- `app/static/inbox/styles.css`
- `app/static/inbox/img/brasao.png`
- `app/static/inbox/img/sti_logo.png`

### Infra
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `.dockerignore`
- `.gitignore`
- `requirements.txt`

---

## Validacoes Executadas

Durante a criacao deste guia foram executados:

```bash
python -m compileall app scripts
node --check app/static/inbox/app.js
```

Ambos passaram sem erro de sintaxe. Nao foram executados testes de integracao com banco, n8n, EvolutionAPI ou navegador.
