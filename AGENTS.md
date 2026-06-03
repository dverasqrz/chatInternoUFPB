# Guia para agentes de IA - UFPB Chat System

Este arquivo e o ponto de partida para qualquer agente que for modificar o
projeto. Ele documenta a arquitetura, os parametros configuraveis, os contratos
de API, os fluxos de negocio e as armadilhas conhecidas encontradas durante a
leitura completa do codigo.

## Resumo rapido

O projeto e uma aplicacao FastAPI para atendimento multiatendente via WhatsApp,
com frontend estatico em `/inbox`, banco PostgreSQL via SQLAlchemy, integracao
com EvolutionAPI/n8n, upload de midia, templates de mensagens, exportacao de
conversas e recursos de IA.

Pontos de entrada principais:

- `app/main.py`: cria `app = create_application()`.
- `app/core/app_factory.py`: configura FastAPI, CORS, static files, rotas,
  handlers de excecao e startup/shutdown.
- `app/core/config.py`: define todos os parametros de ambiente em `Settings`.
- `app/services/messages.py`: coracao da ingestao de webhooks e do envio
  outbound para n8n.
- `app/static/inbox/index.html`, `app/static/inbox/app.js`,
  `app/static/inbox/styles.css`: frontend vanilla JS servido por FastAPI.
- `docker-compose.yml` e `Dockerfile`: empacotamento atual.

Comandos uteis:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
python -m compileall app scripts
node --check app/static/inbox/app.js
docker compose up -d --build
```

## Inicializacao da aplicacao

`create_application()` cria uma instancia de `ApplicationFactory`, que executa:

1. `get_settings()` para carregar `.env`.
2. `setup_logging(settings)`.
3. `FastAPI(...)` com docs em `/api/v1/docs`, redoc em `/api/v1/redoc` e
   openapi em `/api/v1/openapi.json`.
4. CORS via `Settings.cors_*`.
5. Middleware HTTP de logging detalhado.
6. Static files:
   - `/inbox` -> `app/static/inbox`, com `html=True`.
   - `/uploads` -> `settings.media_storage_path`.
7. Rotas de API e webhooks publicos.
8. Exception handlers globais.
9. Lifespan de startup:
   - espera o banco responder `SELECT 1`;
   - roda `Base.metadata.create_all(bind=engine)`;
   - aplica `ensure_schema_compatibility(engine)`;
   - cria admin inicial com `ensure_initial_admin_user(db)`;
   - cria/carrega `RuntimeSettings`;
   - cria templates de sistema;
   - sincroniza webhooks de ambiente para o banco;
   - garante diretorio de midia.

Ao acessar `/`, a aplicacao redireciona para `/inbox`.

## Estrutura de diretorios

- `app/api/deps.py`: dependencias FastAPI de auth e sessao.
- `app/api/routes/`: routers por dominio.
- `app/core/`: config, factory, logging, excecoes e utilitarios de seguranca
  mais genericos.
- `app/db/`: base declarativa e sessao SQLAlchemy.
- `app/models/`: modelos SQLAlchemy.
- `app/schemas/`: modelos Pydantic usados nas APIs.
- `app/services/`: regras de negocio e integracoes.
- `app/services/media/`: servico centralizado de upload/midia.
- `app/static/inbox/`: UI web vanilla JS.
- `scripts/`: scripts de diagnostico, testes manuais e suporte operacional.
- `uploads/`, `runtime/`, `logs/`: diretorios de runtime, ignorados no git.

## Configuracao e parametros de ambiente

Todas as configuracoes reais vivem em `app/core/config.py`. O `Settings` usa
`pydantic-settings`, le `.env`, ignora campos extras e e case-insensitive.

### Aplicacao

| Variavel | Campo | Tipo/default | Efeito |
| --- | --- | --- | --- |
| `APP_NAME` | `app_name` | `str`, `UFPB Chat Multiatendente` | Nome exibido nos metadados FastAPI. |
| `APP_VERSION` | `app_version` | `str`, `2.0.0` | Versao logica da aplicacao. |
| `API_V1_PREFIX` | `api_v1_prefix` | `str`, `/api/v1` | Prefixo das rotas versionadas. |
| `ENVIRONMENT` | `environment` | `development`, `production` ou `testing` | Controla logging em arquivo quando `production`. |
| `DEBUG` | `debug` | `bool`, `False` | Exposto em `/api/v1/auth/config`; nao liga debug automaticamente no uvicorn de producao. |
| `LOG_LEVEL` | `log_level` | `str`, `INFO` | Nivel de log raiz. |

### Banco de dados

| Variavel | Campo | Tipo/default | Efeito |
| --- | --- | --- | --- |
| `DATABASE_URL` | `database_url` | `str`, PostgreSQL local | Usado por `create_engine`. |
| `DATABASE_POOL_SIZE` | `database_pool_size` | `int`, `5` | Declarado, mas nao passado atualmente ao `create_engine`. |
| `DATABASE_MAX_OVERFLOW` | `database_max_overflow` | `int`, `10` | Declarado, mas nao usado atualmente. |
| `DATABASE_POOL_TIMEOUT` | `database_pool_timeout` | `int`, `30` | Declarado, mas nao usado atualmente. |

`app/db/session.py` cria `engine = create_engine(settings.database_url,
pool_pre_ping=True)` e `SessionLocal` com `autocommit=False`,
`autoflush=False`, `expire_on_commit=False`.

### Seguranca e sessoes

| Variavel | Campo | Tipo/default | Efeito |
| --- | --- | --- | --- |
| `SECRET_KEY` | `secret_key` | `str`, `change-me-in-production` | Assina JWTs. Trocar invalida tokens atuais. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `access_token_expire_minutes` | `int`, 30 dias | Validade do token usado pelo frontend. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `refresh_token_expire_days` | `int`, `7` | Usado apenas em `app/core/security.py`; a auth principal nao emite refresh token. |
| `PASSWORD_MIN_LENGTH` | `password_min_length` | `int`, `8` | Usado por `validate_password_strength` em `app/core/security.py`; rotas atuais usam validacao Pydantic minima. |

Ha duas camadas de seguranca:

- `app/utils/security.py`: usada de fato pelas rotas de auth (`hash_password`,
  `verify_password`, `create_access_token`, `decode_access_token`). Token contem
  `sub` e `exp`, sem campo `type`.
- `app/core/security.py`: utilitarios mais genericos e parcialmente nao usados
  pelas rotas atuais. Seus tokens incluem `type` (`access`, `refresh`,
  `password_reset`).

Nao misture as duas APIs sem revisar o formato do JWT.

### Admin inicial

| Variavel | Campo | Tipo/default | Efeito |
| --- | --- | --- | --- |
| `ADMIN_NAME` | `admin_name` | `str`, `Admin Principal` | Nome do admin criado no primeiro boot. |
| `ADMIN_EMAIL` | `admin_email` | `str`, `admin@example.com` | Email unico do admin inicial. |
| `ADMIN_BOOTSTRAP_FILE` | `admin_bootstrap_file` | `Path`, `/app/runtime/admin_bootstrap.txt` | Arquivo onde a senha gerada e gravada. |

Importante: `ADMIN_PASSWORD` aparece no README, mas nao existe em `Settings` e
nao e usado pelo codigo atual. O admin inicial recebe uma senha aleatoria gerada
por `ensure_initial_admin_user()` e escrita em `ADMIN_BOOTSTRAP_FILE`.

### Webhooks n8n/EvolutionAPI

| Variavel | Campo | Tipo/default | Efeito |
| --- | --- | --- | --- |
| `WEBHOOK_TOKEN` | `webhook_token` | `str | None` | Token inbound; aceito em `x-webhook-token`, `x-token`, `Authorization: Bearer` ou query `?token=`. Vazio vira `None`. |
| `WEBHOOK_TIMEOUT` | `webhook_timeout` | `int`, `30` | Declarado, mas nao usado diretamente nas chamadas atuais. |
| `WEBHOOK_RETRY_ATTEMPTS` | `webhook_retry_attempts` | `int`, `3` | Declarado, mas sem retry implementado atualmente. |
| `N8N_WEBHOOK_MODE` | `n8n_webhook_mode` | `test` ou `prod`, default `prod` | Seleciona os campos `_TEST` ou `_PROD`. |
| `N8N_INBOUND_WEBHOOK_URL_TEST` | `n8n_inbound_webhook_url_test` | URL opcional | URL informativa inbound em modo test. |
| `N8N_INBOUND_WEBHOOK_URL_PROD` | `n8n_inbound_webhook_url_prod` | URL opcional | URL informativa inbound em modo prod. |
| `N8N_OUTBOUND_WEBHOOK_URL_TEST` | `n8n_outbound_webhook_url_test` | URL opcional | URL para POST outbound em modo test. |
| `N8N_OUTBOUND_WEBHOOK_URL_PROD` | `n8n_outbound_webhook_url_prod` | URL opcional | URL para POST outbound em modo prod. |
| `N8N_OUTBOUND_AUTH_TYPE` | `n8n_outbound_auth_type` | `none`, `header`, `basic`, `jwt` | Tipo de auth usado ao chamar n8n. Valores invalidos viram `none`. |
| `N8N_OUTBOUND_AUTH_HEADER_NAME` | `n8n_outbound_auth_header_name` | `str | None` | Nome do header se auth `header`. |
| `N8N_OUTBOUND_AUTH_HEADER_VALUE` | `n8n_outbound_auth_header_value` | `str | None` | Valor do header se auth `header`. |
| `N8N_OUTBOUND_AUTH_BASIC_USERNAME` | `n8n_outbound_auth_basic_username` | `str | None` | Usuario Basic Auth. |
| `N8N_OUTBOUND_AUTH_BASIC_PASSWORD` | `n8n_outbound_auth_basic_password` | `str | None` | Senha Basic Auth. |
| `N8N_OUTBOUND_AUTH_JWT_TOKEN` | `n8n_outbound_auth_jwt_token` | `str | None` | Token Bearer se auth `jwt`. |

Atencao: `.env.example` e README citam `N8N_INBOUND_WEBHOOK_URL` e
`N8N_OUTBOUND_WEBHOOK_URL`. Esses nomes sem `_TEST`/`_PROD` nao sao campos
reais do `Settings`; por causa de `extra="ignore"`, eles tendem a ser
ignorados. Use os campos `_TEST`/`_PROD` e selecione com `N8N_WEBHOOK_MODE`.

Prioridade efetiva:

1. Variaveis de ambiente, quando existem, sobrescrevem dados em
   `runtime_settings`.
2. Se nao houver env para outbound URL/token inbound, usa o banco.
3. Admin pode alterar configuracoes em `/api/v1/admin/webhook-settings`, mas
   env continua tendo prioridade no proximo carregamento.

### IA

| Variavel | Campo | Tipo/default | Efeito |
| --- | --- | --- | --- |
| `AI_WEBHOOK_MODE` | `ai_webhook_mode` | `test` ou `prod`, default `prod` | Seleciona URL de consulta IA. |
| `AI_WEBHOOK_URL_TEST` | `ai_webhook_url_test` | URL opcional | Webhook n8n para `/api/v1/ai/ask` em test. |
| `AI_WEBHOOK_URL_PROD` | `ai_webhook_url_prod` | URL opcional | Webhook n8n para `/api/v1/ai/ask` em prod. |
| `AI_AGENT_WEBHOOK_URL_TEST` | `ai_agent_webhook_url_test` | URL opcional | Webhook de agente automatico em test. |
| `AI_AGENT_WEBHOOK_URL_PROD` | `ai_agent_webhook_url_prod` | URL opcional | Webhook de agente automatico em prod. |
| `AI_WEBHOOK_USERNAME` | `ai_webhook_username` | `str | None` | Basic Auth opcional para consulta IA. |
| `AI_WEBHOOK_PASSWORD` | `ai_webhook_password` | `str | None` | Basic Auth opcional para consulta IA. |
| `OLLAMA_BASE_URL` | `ollama_base_url` | `https://ollama.sti.ufpb.br/` | Usado em `/api/v1/ai/fetch-models?provider=ollama`. |

O provedor ativo (`gemini`, `openai`, `groq`, `ollama`) e o toggle do agente
automatico ficam no banco em `RuntimeSettings` e sao administrados por
`/api/v1/admin/ai-settings`.

### Midia

| Variavel | Campo | Tipo/default | Efeito |
| --- | --- | --- | --- |
| `MEDIA_STORAGE_PATH` | `media_storage_path` | `Path`, `/app/uploads` | Diretorio montado como `/uploads`. |
| `MEDIA_MAX_FILE_SIZE` | `media_max_file_size` | `int`, 25 MB | Limite no servico central de upload. |
| `MEDIA_ALLOWED_EXTENSIONS` | `media_allowed_extensions` | lista default | Declarada no settings; o servico de midia tambem mantem listas internas por tipo. |

Rota ativa de upload: `uploads_v2`. Ela usa `MediaService.upload_media()` e
rejeita videos. A rota antiga `app/api/routes/uploads.py` aceita video bruto,
mas nao e registrada em `ApplicationFactory`.

### CORS, rate limit e externos

| Variavel | Campo | Tipo/default | Efeito |
| --- | --- | --- | --- |
| `CORS_ORIGINS` | `cors_origins` | `str`, `*` | String separada por virgulas ou `*`. |
| `CORS_ALLOW_CREDENTIALS` | `cors_allow_credentials` | `bool`, `True` | Usado pelo middleware CORS. |
| `CORS_ALLOW_METHODS` | `cors_allow_methods` | `list[str]`, `["*"]` | Usado pelo middleware CORS. |
| `CORS_ALLOW_HEADERS` | `cors_allow_headers` | `list[str]`, `["*"]` | Usado pelo middleware CORS. |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `rate_limit_requests_per_minute` | `int`, `60` | Declarado; nao aplicado globalmente. |
| `RATE_LIMIT_BURST_SIZE` | `rate_limit_burst_size` | `int`, `10` | Declarado; nao aplicado globalmente. |
| `PUBLIC_DOMAIN` | `public_domain` | `str | None` | Retornado em `/api/v1/auth/config`; frontend usa como base absoluta se presente. |
| `REDIS_URL` | `redis_url` | `str | None` | Declarado; sem uso atual. |
| `CELERY_BROKER_URL` | `celery_broker_url` | `str | None` | Declarado; sem uso atual. |

## Banco de dados e modelos

O banco e criado automaticamente por `Base.metadata.create_all()`. O projeto
tambem tem uma migracao Alembic apenas para `message_templates`, mas nao ha
configuracao Alembic completa visivel na raiz.

### `users`

Modelo: `app/models/user.py`.

- `id`: PK.
- `name`: nome do usuario, max 120.
- `email`: unico, indexado, max 255.
- `password_hash`: hash bcrypt.
- `must_change_password`: bloqueia rotas que dependem de
  `get_current_user_password_changed`.
- `is_admin`: libera rotas administrativas.
- `is_active`: usuarios inativos recebem 403.
- `last_login_at`: atualizado no login.
- `last_logout_at`: atualizado no logout.
- `last_interaction_at`: usado para expirar sessao depois de 7 dias sem
  interacao.
- `created_at`, `updated_at`: timestamps do banco.
- Relacao: `outbound_messages` com `Message.attendant`.

### `conversations`

Modelo: `app/models/conversation.py`.

- `id`: PK.
- `contact_phone`: unico, indexado, formato normalizado `+<digitos>`.
- `contact_name`: opcional.
- `profile_picture_url`: opcional.
- `created_at`: timestamp.
- `last_message_at`: usado para ordenar inbox.
- Relacao: `messages` com cascade `all, delete-orphan`.

### `messages`

Modelo: `app/models/message.py`.

Enums:

- `MessageDirection`: `inbound`, `outbound`.
- `MessageType`: `text`, `image`, `audio`, `video`, `document`.
- `DeliveryStatus`: `received`, `queued`, `sent`, `delivered`, `read`,
  `failed`.

Campos:

- `id`: PK.
- `conversation_id`: FK para `conversations.id`.
- `direction`: origem da mensagem.
- `message_type`: tipo logico.
- `delivery_status`: status atual.
- `text_content`: texto.
- `media_url`: URL local `/uploads/...` ou URL externa.
- `media_mime_type`: MIME normalizado.
- `media_caption`: legenda.
- `sender_name`, `sender_phone`: origem exibida.
- `attendant_id`: FK para `users.id` em mensagens outbound.
- `external_message_id`: ID vindo do WhatsApp/Evolution; usado para dedupe,
  status update e revogacao.
- `raw_payload`: payload original ou metadados da API.
- `error_message`: erro de envio outbound.
- `created_at`: timestamp.

### `runtime_settings`

Modelo: `app/models/runtime_settings.py`.

Registro singleton com `id=1`.

- Campos outbound webhook: URL e auth (`none`, `header`, `basic`, `jwt`).
- `inbound_webhook_token`: token de entrada se nao vier por env.
- Campos IA: `ai_agent_enabled`, `ai_provider`, `ai_api_key`,
  `ai_base_url`, `ai_model`.
- `updated_at`.

`app/services/runtime_settings.py` mantem cache em memoria. Sempre chame
`invalidate_runtime_cache()` depois de escrita administrativa. Quando for
alterar settings dentro de uma rota, carregue o objeto na sessao atual com
`db.get(RuntimeSettings, 1)` para evitar objeto cacheado de outra sessao.

### `message_templates`

Modelo: `app/models/template.py`.

- `id`: PK.
- `title`: max 200.
- `content`: texto.
- `category`: max 50.
- `is_active`: controla listagem normal.
- `is_system`: marca templates criados pelo sistema.
- `created_at`, `updated_at`.
- `created_by`: ID do usuario criador, sem FK declarada.

Observacao importante: comentarios e docstrings dizem que templates de sistema
nao podem ser apagados/editados, mas `TemplateService.update_template()` e
`delete_template()` removeram essa protecao. A rota ainda menciona protecao, mas
o servico permite a alteracao/exclusao.

## Dependencias e autorizacao

Arquivo: `app/api/deps.py`.

- `oauth2_scheme`: espera `Authorization: Bearer <token>`, tokenUrl
  `/api/v1/auth/login`.
- `get_current_user(db, token)`: decodifica token com `app/utils/security.py`,
  exige `sub` numerico, usuario ativo e sessao sem mais de 7 dias de
  inatividade desde `last_interaction_at` ou `last_login_at`.
- `get_current_user_password_changed(current_user)`: bloqueia se
  `must_change_password=True`.
- `get_current_admin(current_user)`: exige `is_admin=True`.

Use a dependencia mais restritiva compativel com o endpoint. Rotas de leitura
basica podem usar `get_current_user`; rotas de operacao normal devem usar
`get_current_user_password_changed`; administracao deve usar `get_current_admin`.

## Rotas HTTP

Todas as rotas abaixo usam prefixo `/api/v1`, exceto `/health`, `/webhook`,
`/webhook/`, `/api/inbox` e `/api/inbox/`.

### Auth

Router: `app/api/routes/auth.py`, prefixo `/auth`.

- `GET /auth/challenge`
  - Publico.
  - Retorna `challenge_id`, `question`, `expires_in_seconds`.
  - Headers anti-cache.
  - O desafio expira em 120s e e consumido em uma tentativa.

- `POST /auth/login`
  - Publico.
  - Body `LoginRequest`:
    - `email: EmailStr`
    - `password: str`, 1..128
    - `challenge_id: str`, 3..128
    - `challenge_answer: str`, 1..20
  - Valida desafio, email/senha, usuario ativo.
  - Atualiza `last_login_at` e `last_interaction_at`.
  - Retorna `TokenResponse`.

- `GET /auth/me`
  - Auth: `get_current_user`.
  - Retorna `UserRead`.

- `GET /auth/config`
  - Publico.
  - Retorna `public_domain`, `api_prefix`, `environment`, `debug`.

- `POST /auth/change-password`
  - Auth: `get_current_user`.
  - Body `ChangePasswordRequest`:
    - `current_password: str`, 1..128
    - `new_password: str`, 8..128, diferente da atual.
  - Atualiza hash, remove `must_change_password`, atualiza interacao.

- `POST /auth/logout`
  - Auth: `get_current_user`.
  - Atualiza `last_logout_at`.

### Users

Router: `app/api/routes/users.py`, prefixo `/users`.

- `GET /users?active_only=true`
  - Auth: admin.
  - Query `active_only: bool = true`.
  - Lista usuarios, ordenados por `created_at desc`.

- `POST /users`
  - Auth: admin.
  - Body `UserCreate`: `name` 2..120, `email`, `password` 8..128.
  - Cria usuario comum ativo com `must_change_password=True`.

- `POST /users/{user_id}/reset-password`
  - Auth: admin.
  - Body `AdminResetPasswordRequest`: `new_password` 8..128.
  - Nao permite resetar a propria senha por esta rota.
  - Marca `must_change_password=True`.

- `PATCH /users/{user_id}/status`
  - Auth: admin.
  - Body `AdminUserStatusUpdateRequest`: `is_active: bool`.
  - Nao permite auto-desativacao.

- `DELETE /users/{user_id}`
  - Auth: admin.
  - Nao permite excluir a si mesmo nem outro admin.

### Conversations e messages

Router: `app/api/routes/conversations.py`, prefixo `/conversations`.

- `GET /conversations?limit=50&offset=0`
  - Auth: senha ja trocada.
  - `limit`: 1..200.
  - `offset`: >=0.
  - Lista apenas conversas que possuem mensagens.

- `POST /conversations`
  - Auth: senha ja trocada.
  - Body `ConversationCreate`:
    - `contact_phone: str`
    - `contact_name: str | None`
  - Normaliza telefone usando `_normalize_phone`.
  - Para Brasil, procura variacao com/sem nono digito antes de criar.

- `GET /conversations/contacts/all`
  - Auth: senha ja trocada.
  - Lista todos os contatos/conversas, mesmo sem mensagens.

- `GET /conversations/search/messages?q=abc`
  - Auth: senha ja trocada.
  - Query `q`: min 3 caracteres.
  - Busca em `Message.text_content ilike %q%`, max 50.

- `GET /conversations/{conversation_id}/messages?limit=100&offset=0`
  - Auth: senha ja trocada.
  - `limit`: 1..500.
  - Retorna mensagens em ordem cronologica, mesmo buscando do banco em ordem
    desc.

- `POST /conversations/{conversation_id}/messages`
  - Auth: senha ja trocada.
  - Body `OutboundMessageCreate`:
    - `message_type`: default `text`.
    - `text_content`: opcional, max 6000.
    - `media_url`: opcional.
    - `media_mime_type`: opcional, max 150.
    - `media_caption`: opcional, max 2000.
  - Validacao:
    - `text` exige `text_content`.
    - `image`, `audio`, `video` exigem `media_url`.
    - `document` nao e exigido explicitamente pelo validator, mas o frontend
      envia `media_url`.
  - Cria mensagem outbound e posta para n8n se houver URL configurada.

- `POST /conversations/{conversation_id}/messages/delete-selected`
  - Auth: admin.
  - Body `MessageBulkDeleteRequest`: `message_ids` 1..500, inteiros positivos,
    deduplicados e ordenados pelo validator.
  - Apaga mensagens selecionadas. Se conversa ficar vazia, remove a conversa.

- `POST /conversations/{conversation_id}/messages/{message_id}/revoke`
  - Auth: senha ja trocada.
  - Exige `external_message_id`.
  - Monta payload `delete_for_everyone` para n8n.
  - Se outbound webhook responder OK, marca mensagem local como texto
    `"🚫 Essa mensagem foi apagada"` e remove midia.

- `DELETE /conversations/{conversation_id}/messages/all`
  - Auth: admin.
  - Apaga todas as mensagens da conversa; remove conversa se ficar vazia.

- `DELETE /conversations/messages/all`
  - Auth: admin.
  - Apaga todas as mensagens e todas as conversas.

- `GET /conversations/{conversation_id}/export`
  - Auth: senha ja trocada.
  - Query obrigatoria `export_date: date`.
  - Query opcional `start_time=00:00`, `end_time=23:59`,
    `contact_profile=indefinido`.
  - Retorna JSON `ConversationExportResponse`.

- `GET /conversations/{conversation_id}/export/pdf`
  - Auth: senha ja trocada.
  - Mesmos parametros da exportacao JSON.
  - Retorna PDF gerado com ReportLab.

### Webhooks

Router versionado: `/api/v1/webhooks`. Router publico sem prefixo:
`/webhook`, `/webhook/`, `/api/inbox`, `/api/inbox/`.

- `POST /api/v1/webhooks/evolution`
- `POST /webhook`
- `POST /api/inbox`

Parametros:

- Body: `dict[str, Any]`, payload bruto EvolutionAPI/n8n.
- Headers aceitos para token:
  - `x-webhook-token`
  - `x-token`
  - `Authorization: Bearer <token>`
- Query:
  - `token=<token>`

Fluxo:

1. `_validate_inbound_token()` carrega token efetivo via env/banco.
2. Se nao ha token configurado, aceita sem autenticacao de webhook.
3. `ingest_inbound_message(db, payload)` normaliza e persiste evento.
4. Sempre agenda `_forward_to_ai_agent(payload)` em background; o forward so
   executa se `RuntimeSettings.ai_agent_enabled=True` e houver URL de agente IA
   no ambiente.
5. Responde `WebhookIngestResponse`.

### Templates

Router: `app/api/routes/templates.py`, prefixo `/templates`.

- `GET /templates/?include_inactive=false`
  - Auth: usuario autenticado, nao exige senha trocada.
  - Retorna `MessageTemplateList`.

- `GET /templates/{template_id}`
  - Auth: usuario autenticado.

- `POST /templates/`
  - Auth: admin.
  - Body `MessageTemplateCreate`: `title` 1..200, `content` min 1,
    `category` 1..50.

- `PUT /templates/{template_id}`
  - Auth: admin.
  - Body `MessageTemplateUpdate`: campos opcionais `title`, `content`,
    `category`, `is_active`.

- `DELETE /templates/{template_id}`
  - Auth: admin.

- `GET /templates/category/{category}`
  - Auth: usuario autenticado.
  - Lista templates ativos da categoria exata.

- `POST /templates/initialize`
  - Auth: admin.
  - Cria templates LGPD/Pesquisa se nao existirem.

### Admin

Router: `app/api/routes/admin.py`, prefixo `/admin`.

- `GET /admin/webhook-settings`
  - Auth: admin.
  - Retorna config sem expor segredos completos; usa previews.

- `PUT /admin/webhook-settings`
  - Auth: admin.
  - Body `WebhookSettingsUpdate`:
    - `outbound_webhook_url`: opcional, max 1000.
    - `outbound_auth_type`: `none`, `header`, `basic`, `jwt`.
    - `outbound_auth_header_name`: max 100.
    - `outbound_auth_header_value`: max 1000.
    - `outbound_auth_basic_username`: max 255.
    - `outbound_auth_basic_password`: max 1000.
    - `outbound_auth_jwt_token`: max 2000.
    - `inbound_webhook_token`: max 255.
  - Strings vazias viram `None`.
  - Valida requisitos por tipo de auth.
  - Invalida cache de runtime.

- `GET /admin/ai-settings`
  - Auth: admin.
  - Retorna `ai_provider` e `ai_agent_enabled`.

- `PUT /admin/ai-settings`
  - Auth: admin.
  - Body `AISettingsUpdate`: `ai_provider` opcional (`gemini`, `openai`,
    `groq`, `ollama`) e `ai_agent_enabled` opcional.
  - Invalida cache.

- `DELETE /admin/cleanup/messages`
  - Auth: admin.
  - Apaga todas as mensagens.

- `DELETE /admin/cleanup/uploads`
  - Auth: admin.
  - Apaga todos os itens de `/app/uploads`. Caminho fixo, nao usa
    `settings.media_storage_path`.

- `DELETE /admin/cleanup/contacts`
  - Auth: admin.
  - Apaga todas as conversas/contatos. Pelo relacionamento, mensagens devem ser
    removidas em cascade quando ORM/cascade estiver ativo.

### Uploads

Router ativo: `app/api/routes/uploads_v2.py`, prefixo `/uploads`.

- `POST /uploads/media`
  - Auth: senha ja trocada.
  - Multipart `file: UploadFile`.
  - Usa `MediaService.upload_media(file, convert_video=False)`.
  - Valida tipo, extensao e tamanho.
  - Rejeita video.
  - Retorna `UploadMediaResponse`: `filename`, `media_url`, `mime_type`,
    `size_bytes`.

- `GET /uploads/media/{filename}`
  - Auth: senha ja trocada.
  - Retorna metadados do arquivo.

- `DELETE /uploads/media/{filename}`
  - Auth: senha ja trocada.
  - Apaga arquivo pelo nome.

- `POST /uploads/cleanup?days=30`
  - Auth: usuario com senha trocada e `is_admin=True` checado manualmente.
  - Remove arquivos antigos.

### WhatsApp tools

Router: `app/api/routes/whatsapp_tools.py`, prefixo `/whatsapp`.

- `POST /whatsapp/status-media`
  - Auth: senha ja trocada.
  - Multipart `file`.
  - Rejeita `video/*`.
  - Usa `MediaService`.

- `GET /whatsapp/media-info`
  - Auth: senha ja trocada.
  - Retorna tipos suportados; video aparece como desativado.

### IA

Router: `app/api/routes/ai.py`, prefixo `/ai`.

- `POST /ai/ask`
  - Auth: senha ja trocada.
  - Body `AIQuestionRequest`: `question: str`.
  - Seleciona URL por `AI_WEBHOOK_MODE`.
  - Envia payload para n8n com pergunta, usuario e provider ativo.
  - Basic Auth opcional via `AI_WEBHOOK_USERNAME`/`AI_WEBHOOK_PASSWORD`.
  - Timeout de 120s.
  - Aceita resposta JSON com `output`, `response` ou `answer`; se nao for JSON,
    usa texto bruto.

- `GET /ai/fetch-models?provider=...&key=...`
  - Auth: senha ja trocada.
  - Para `provider=ollama`, chama `${OLLAMA_BASE_URL}/api/tags`.
  - Para demais, retorna listas default. `key` e aceito mas nao usado.

### Health

- `GET /health`: retorna `{"status": "ok"}`.
- `GET /health/integrations`: mostra URLs/mode detectados para n8n inbound e
  outbound de ambiente.

## Servico de mensagens e webhooks

Arquivo: `app/services/messages.py`.

### Normalizacao de telefone

`_normalize_phone(raw)`:

- Remove tudo que nao for digito.
- Se tiver 10 ou 11 digitos e nao comecar por `55`, adiciona `55`.
- Para telefones brasileiros que comecam por `55`, tem 13 digitos e possuem
  nono digito na posicao esperada, remove o nono digito quando DDD > 28. Isso
  segue uma regra de JID do WhatsApp citada no codigo.
- Retorna `+<digitos>` ou `None`.

Nao mude essa funcao sem revisar criacao manual de conversas, deduplicacao de
contatos e ingestao de webhooks.

### Tipos e midia

`_extract_type(raw_type, has_media, message)` detecta `document`, `image`,
`audio`, `video` e cai para `text`.

`_persist_inbound_media_from_base64(payload, message_type, mime_type)`:

- Procura base64 em chaves `base64`, `media_base64`, `file_base64`,
  `mediabase64`, `filebase64`, recursivamente.
- Se nao achar, tenta buscar na EvolutionAPI usando `server_url`, `apikey`,
  `instance` e `message_id` com endpoint
  `/chat/getBase64FromMediaMessage/{instance}`.
- Rejeita midia maior que 25 MB.
- Salva em `settings.media_storage_path`.
- Retorna `/uploads/<filename>`.
- Para video, hoje apenas salva bruto e retorna URL; comentarios indicam modo
  de teste sem conversao.

### Payloads suportados

`normalize_webhook_payload(payload)` suporta:

- `contacts.upsert` e `contacts.update`:
  - Extrai telefone, nome e foto de perfil.
  - Retorna evento de atualizacao de contato sem mensagem.

- `messages.update`:
  - Extrai `external_message_id`, telefone e status.
  - Mapeia status numerico/string para `FAILED`, `QUEUED`, `SENT`,
    `DELIVERED`, `READ`.

- `messages.delete`:
  - Extrai `external_message_id`.
  - Ingestao marca a mensagem como apagada localmente.

- Demais eventos de mensagem:
  - Procura dados em `payload.data`, `payload.body.data`, `payload.body` ou
    raiz.
  - Extrai `key`, `sender`, `message`, `extendedTextMessage`,
    `imageMessage`, `audioMessage`, `videoMessage`, `documentMessage`.
  - Define `direction` por `key.fromMe`/`root.fromMe`.
  - Se o sender normalizado for `+558332167336`, forca `from_me=True`.
  - Se texto ausente em mensagem `text`, grava `[mensagem sem texto]`.

### Ingestao inbound

`ingest_inbound_message(db, payload)`:

- Chama `normalize_webhook_payload`.
- Rejeita payload sem telefone.
- Ignora contato `+558332167336`. Este numero esta hardcoded como numero do
  bot/institucional para evitar loop.
- Ignora evento em que `contact_phone` e igual ao sender normalizado do payload.
- Em `messages.update`, atualiza status de mensagem por `external_message_id`.
- Em `messages.delete`, marca como `"🚫 Essa mensagem foi apagada"` e remove
  midia.
- Cria ou atualiza `Conversation`.
- Atualiza `profile_picture_url` se vier no payload.
- Se nao houver foto local, tenta buscar na EvolutionAPI em
  `/chat/fetchProfilePictureUrl/{instance}`.
- Em `contacts.upsert`/`contacts.update`, retorna a conversa sem criar
  mensagem.
- Atualiza `conversation.last_message_at`.
- Evita duplicata por `external_message_id`.
- Para webhook outbound recente sem `external_message_id`, tenta casar mensagem
  existente da mesma conversa nos ultimos 5 minutos pelo mesmo texto e atualiza
  o ID externo.
- Cria `Message` com `RECEIVED` para inbound e `SENT` para outbound confirmado.

### Envio outbound

`create_outbound_message(db, conversation, attendant, data)`:

- Cria mensagem `OUTBOUND` com status inicial `QUEUED`.
- Atualiza `conversation.last_message_at` e `attendant.last_interaction_at`.
- Carrega `RuntimeSettings` e URL outbound efetiva.
- Se nao houver URL outbound, marca `SENT` e retorna.
- Monta payload para n8n:
  - `conversation_id`
  - `message_id`
  - `to`
  - `message_type`
  - `text`
  - `media_url`
  - `media_mime_type`
  - `media_caption`
  - `attendant`
- Auth outbound:
  - `header`: adiciona header configurado.
  - `basic`: usa tuple `(username, password)` do httpx.
  - `jwt`: adiciona `Authorization: Bearer <token>`.
- POST com timeout 20s.
- Sucesso -> `SENT`.
- `httpx.HTTPError` -> `FAILED` e grava `error_message`.

## Frontend `/inbox`

O frontend e vanilla JS, sem build step. FastAPI serve `index.html`, `app.js` e
`styles.css` diretamente.

### Estado global

`app/static/inbox/app.js` define:

- `apiPrefix = "/api/v1"`.
- `state.token`: JWT no `localStorage` (`ufpb_token`).
- `state.user`: usuario logado.
- `state.conversations`: conversas da sidebar.
- `state.catalogContacts`: criado dinamicamente em `loadCatalog()`.
- `state.messagesByConversation`: cache por conversa.
- `state.selectedConversationId`: conversa ativa.
- `state.messageSignaturesByConversation`: assinatura para evitar rerender.
- `state.passwordForced`: controla modal de troca obrigatoria.
- `state.loginChallengeId`: desafio atual.
- `state.messagePollTimer`: polling de mensagens a cada 2s.
- `state.conversationPollTimer`: polling de conversas a cada 5s.
- `state.messageOffsets`, `state.hasMoreMessages`, `state.messagesPerPage`:
  scroll infinito de mensagens.
- `state.audioContext`, `state.analyser`, `state.activeRecorder`,
  `state.activeStream`: gravacao de audio.
- `state.messageTemplates`: templates carregados do backend ou fallback local.
- `state.publicConfig`: resposta de `/auth/config`; se `public_domain` existe,
  `apiRequest()` usa URL absoluta.

### Mapa `els`

`els` faz `document.getElementById(...)` para quase toda a UI. Qualquer mudanca
em IDs no HTML precisa ser refletida em `app.js`. Grupos sensiveis:

- Login: `loginOverlay`, `loginForm`, `loginEmail`, `loginPassword`,
  `challengeQuestion`, `challengeAnswer`, `refreshChallengeBtn`.
- Senha: `passwordOverlay`, `passwordForm`, `currentPassword`, `newPassword`.
- Admin usuarios: `adminSection`, `adminUsersTableBody`, `newUserName`,
  `newUserEmail`, `newUserPassword`.
- Conversas/mensagens: `conversationList`, `chatTitle`, `chatSubtitle`,
  `messageCountBadge`, `messages`.
- Composer: `messageType`, `textContent`, `mediaUrl`, `mediaCaption`,
  `mediaMimeType`, `imageFileInput`, `uploadImageBtn`, `recordAudioBtn`,
  `sendMessageBtn`.
- Templates: `templatesOverlay`, `templatesList`, `openTemplatesManagerBtn`.
- Exportacao: `exportOverlay`, `exportDate`, `exportStartTime`,
  `exportEndTime`, `exportProfile`.
- IA: `aiConsultOverlay`, `aiQuestion`, `aiResponse`, `aiHistory`,
  `configAiProvider`, `configAiAgentEnabled`.

### Fluxo de login no frontend

1. `bootstrap()` chama `fetchLoginChallenge(true)`.
2. Se nao ha token, mostra `loginOverlay`.
3. `login(email, password)` exige desafio carregado e resposta preenchida.
4. POST `/auth/login`.
5. Salva token/usuario em localStorage.
6. Se `must_change_password`, abre modal obrigatorio.
7. Caso contrario chama `initializeInbox()`.

### Inicializacao da inbox

`initializeInbox()`:

- limpa polls antigos;
- carrega `/auth/config`;
- carrega templates;
- se admin, carrega usuarios e AI settings;
- carrega conversas;
- inicia polling:
  - conversas: 5000ms;
  - mensagens: 2000ms;
  - polling de mensagens pausa se houver audio/video tocando.

### Mensagens e renderizacao

- `loadMessages()` usa `limit=state.messagesPerPage` e `offset`.
- O backend retorna ordem cronologica.
- `buildMessageSignature()` evita rerender se nada mudou.
- `renderMessages()` suporta render completo, append e prepend.
- Midias:
  - imagem: `<img>`.
  - documento: card com link.
  - audio: `<audio controls>`.
  - texto apagado: classe `deleted-msg`.
- `formatWhatsAppText()` aplica formatacao estilo WhatsApp para negrito,
  italico, tachado e codigo.

### Uploads e gravacao

- `uploadMediaFile(file)` faz POST multipart para `/api/v1/uploads/media`.
- Imagem/documento local usa `uploadImageFromLocal()`.
- Gravacao de audio usa `MediaRecorder`, gera `audio/webm` e anexa via upload.
- Video recording esta desativado no JS.

### Templates

- Digitar exatamente `/` no campo de texto abre o modal de templates.
- `loadTemplates()` primeiro testa backend via `/auth/me`; se falhar, usa
  fallback local LGPD/Pesquisa.
- Admin pode criar, editar e excluir templates no modal.

### IA no frontend

- Botao `Consultar IA` abre modal.
- `askAi()` envia `{question}` para `/api/v1/ai/ask`.
- Historico e apenas em memoria da pagina.
- Admin pode alterar provider e toggle de agente automatico.

### Exportacao

- `exportCurrentDay()` abre modal para data atual.
- HTML e gerado no frontend a partir de `/conversations/{id}/export`.
- PDF e baixado direto de `/conversations/{id}/export/pdf`.

## Scripts e Docker

### Dockerfile

- Base `python:3.12-slim`.
- Instala `ffmpeg`.
- Instala `requirements.txt`.
- Copia `app` e `scripts`.
- Cria `/app/uploads`, `/app/runtime`, `/app/logs`.
- Healthcheck em `/health`.
- CMD roda `python /app/scripts/startup_check.py` e depois uvicorn.

### docker-compose.yml

Servico `automacoes_sti_ufpb_whatsapp_fastapi`:

- build local via `Dockerfile`;
- `env_file: .env`;
- exige `DATABASE_URL`;
- porta `8000:8000`;
- volumes:
  - `./uploads:/app/uploads`
  - `./runtime:/app/runtime`
  - `./logs:/app/logs`
- healthcheck em `/health`.

Nao ha servico Postgres no compose atual; `DATABASE_URL` deve apontar para um
PostgreSQL externo/acessivel.

### scripts

- `scripts/startup_check.py`: verifica diretorios `/app/uploads`,
  `/app/runtime`, `/app/logs` e presenca de FFmpeg. Nao falha se FFmpeg faltar.
- `scripts/verify_dependencies.py`: diagnostico de FFmpeg, FFprobe, pacotes
  Python e recursos do sistema. Mais adequado para Linux/container.
- `scripts/check_ffmpeg.py`: teste detalhado de FFmpeg/FFprobe e conversao.
- `scripts/test_compression.py`: teste historico de compressao de video.
- `scripts/test_webhook.py`: POST manual para `http://127.0.0.1:8000/api/inbox`
  com payload de documento.
- `scripts/debug_download.py`: le payload de stdin e testa download base64 da
  EvolutionAPI.
- `scripts/migrate_enum.py`: adiciona `delivered` e `read` ao enum PostgreSQL
  `delivery_status`.
- `scripts/init_templates.py`: cria templates LGPD/Pesquisa manualmente; hoje o
  startup ja faz isso.
- `scripts/deploy.sh`: script historico de deploy que espera
  `docker-compose.production.yml` e Alembic. Esse arquivo compose nao existe na
  raiz atual.

## Validacoes executadas nesta revisao

Durante a criacao deste guia foram executados:

```bash
python -m compileall app scripts
node --check app/static/inbox/app.js
```

Ambos passaram sem erro de sintaxe. Nao foram executados testes de integracao
com banco, n8n, EvolutionAPI ou navegador.

## Armadilhas conhecidas antes de modificar

1. `N8N_INBOUND_WEBHOOK_URL`, `N8N_OUTBOUND_WEBHOOK_URL` e `ADMIN_PASSWORD`
   aparecem em docs/exemplo, mas nao sao campos efetivos de `Settings`.
2. O numero `+558332167336` esta hardcoded em `app/services/messages.py` para
   evitar loop com o proprio bot. Se o numero institucional mudar, ajuste todos
   os usos.
3. `app/api/routes/uploads.py` e rota legada nao registrada; a ativa e
   `uploads_v2.py`.
4. Upload ativo rejeita videos, mas alguns scripts, comentarios e listas ainda
   falam de conversao de video/FFmpeg.
5. `MediaService.get_media_info()` referencia `video_converter`, que nao esta
   importado/definido. Hoje o caminho so e atingido se um video estiver no
   storage e for consultado.
6. `TemplateService` permite editar/excluir templates de sistema, apesar de
   comentarios/rotas mencionarem protecao.
7. `scripts/deploy.sh` espera `docker-compose.production.yml`, mas o arquivo
   presente e `docker-compose.yml`.
8. `README.md` menciona `docker compose -f docker-compose.production.yml`, que
   tambem nao existe na raiz atual.
9. `app/static/inbox/app.js` declara `escapeHtml` duas vezes. A segunda
   declaracao sobrescreve a primeira.
10. `app/static/inbox/app.js` referencia `recordPreview`, mas `index.html` nao
    contem elemento com `id="recordPreview"`. O fluxo de abrir gravacao pode
    quebrar ao acessar `els.recordPreview.classList`.
11. `revokeMessage()` procura `.message-body`, mas `renderMessages()` nao cria
    wrapper com essa classe. A revogacao ainda atualiza o banco e o polling deve
    refletir depois, mas a atualizacao instantanea local pode falhar.
12. `styles.css` tem blocos de IA duplicados e um trecho com declaracoes
    `transform: scale(1); opacity: 1;` soltas dentro de `@media (max-width:
    768px)`. Navegadores tendem a ignorar declaracoes invalidas, mas evite
    editar essa area sem limpar o bloco.
13. `app/core/security.py` e `app/utils/security.py` geram formatos de JWT
    diferentes. As rotas atuais usam `app/utils/security.py`.
14. `RuntimeSettings` cacheia um objeto SQLAlchemy expunged. Para escrita em
    rotas administrativas, carregue o registro na sessao atual e invalide cache
    apos commit.
15. `Base.metadata.create_all()` cria tabelas automaticamente. Alteracoes de
    schema devem considerar `schema_maintenance.py`, enums PostgreSQL e dados
    existentes.

## Checklist seguro para novos agentes

Antes de alterar:

- Leia este arquivo e o modulo exato que vai tocar.
- Rode `git status --short` e preserve alteracoes locais nao suas.
- Confirme se a rota/servico que voce vai editar esta registrado em
  `ApplicationFactory`.
- Se mexer em env, atualize `Settings`, `.env.example` e documentacao juntos.
- Se mexer em modelo, revise schema Pydantic, rotas, frontend e manutencao de
  schema.
- Se mexer no HTML, revise todas as chaves em `els`.
- Se mexer no fluxo de mensagens, teste inbound, outbound, update de status,
  delete/revoke e deduplicacao por `external_message_id`.
- Se mexer em uploads, teste arquivo permitido, arquivo rejeitado, tamanho
  maximo e URL `/uploads/...`.
- Se mexer em runtime settings, invalide cache apos escrita.

Depois de alterar:

- Rode `python -m compileall app scripts`.
- Rode `node --check app/static/inbox/app.js` se o JS mudou.
- Se possivel, suba a aplicacao e teste:
  - `/health`
  - `/api/v1/docs`
  - login com desafio
  - listagem de conversas
  - envio de mensagem
  - upload de midia
  - webhook inbound com token
  - telas admin se a alteracao afetar admin.

## Mapa rapido de arquivos por responsabilidade

- Auth e usuarios:
  - `app/api/routes/auth.py`
  - `app/api/routes/users.py`
  - `app/api/deps.py`
  - `app/utils/security.py`
  - `app/services/login_challenge.py`
  - `app/services/bootstrap.py`

- Conversas e mensagens:
  - `app/api/routes/conversations.py`
  - `app/api/routes/webhook.py`
  - `app/services/messages.py`
  - `app/services/conversation_export.py`
  - `app/models/conversation.py`
  - `app/models/message.py`
  - `app/schemas/conversation.py`
  - `app/schemas/message.py`

- Admin/settings:
  - `app/api/routes/admin.py`
  - `app/models/runtime_settings.py`
  - `app/schemas/admin.py`
  - `app/services/runtime_settings.py`
  - `app/services/webhook_utils.py`
  - `app/services/webhook_sync.py`

- Templates:
  - `app/api/routes/templates.py`
  - `app/models/template.py`
  - `app/schemas/template.py`
  - `app/services/template_service.py`

- Midia:
  - `app/api/routes/uploads_v2.py`
  - `app/api/routes/whatsapp_tools.py`
  - `app/services/media/media_service.py`
  - `app/schemas/upload.py`

- IA:
  - `app/api/routes/ai.py`
  - `app/schemas/ai.py`
  - `app/schemas/admin.py`
  - `app/services/runtime_settings.py`

- Frontend:
  - `app/static/inbox/index.html`
  - `app/static/inbox/app.js`
  - `app/static/inbox/styles.css`
  - `app/static/inbox/img/brasao.png`
  - `app/static/inbox/img/sti_logo.png`

- Infra:
  - `Dockerfile`
  - `docker-compose.yml`
  - `.env.example`
  - `.dockerignore`
  - `.gitignore`
  - `requirements.txt`
