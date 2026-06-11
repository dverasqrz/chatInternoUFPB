# UFPB Chat System

Sistema de chat institucional da UFPB com integracao WhatsApp, gerenciamento de usuarios e recursos avancados.

## Visao Geral

Aplicacao FastAPI para atendimento multiatendente via WhatsApp. Frontend vanilla JS servido pelo proprio FastAPI, banco PostgreSQL via SQLAlchemy, integracao com EvolutionAPI/n8n para envio/recebimento de mensagens, upload de midia, templates de mensagens, exportacao de conversas (PDF/HTML) e recursos de IA.

**Versao atual:** 2.0.0  
**Stack principal:** Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vanilla JS  
**Infraestrutura:** Docker + EasyPanel  

## Funcionalidades

- **Chat em tempo real** com interface moderna e responsiva
- **Integracao WhatsApp** via EvolutionAPI v2.3.7 + n8n (webhooks inbound/outbound)
- **Multiatendente** com autenticacao por JWT e controle de permissoes
- **Upload de midia** - imagens, audios, documentos (video suportado via webhook, rejeitado no upload manual)
- **Edicao de mensagens** - atendentes editam texto outbound; edicoes do WhatsApp sao refletidas
- **Mensagens citadas (quotes)** - contexto de mensagem respondida preservado
- **Destaque de mensagens nao lidas** - indicador visual por conversa
- **Fotos de perfil** - download e armazenamento local de avatares de contatos
- **Templates de mensagens** - mensagens prontas com trigger por `/`
- **Exportacao** - PDF (ReportLab) e HTML com nome do telefone + data
- **Sistema de IA** - consulta via n8n com toggle de agente automatico
- **Limpeza automatica** - politicas de retencao de midia e mensagens

## Estrutura do Projeto

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
│   │       ├── admin.py            # Configuracoes de webhook/IA, cleanup
│   │       ├── templates.py        # CRUD de templates de mensagens
│   │       ├── uploads_v2.py       # Upload de midia (ativo)
│   │       ├── uploads.py          # Upload legado (nao registrado)
│   │       ├── whatsapp_tools.py   # Status de midia WhatsApp
│   │       ├── ai.py               # Consulta IA
│   │       └── health.py           # Health check
│   ├── core/
│   │   ├── config.py               # Settings (pydantic-settings, .env)
│   │   ├── app_factory.py          # Factory Pattern - criacao do FastAPI
│   │   ├── exceptions.py           # Handlers de excecao globais
│   │   ├── logging.py              # Configuracao de logging
│   │   └── security.py             # Utilitarios de seguranca (genericos)
│   ├── db/
│   │   ├── base.py                 # Base declarativa SQLAlchemy
│   │   └── session.py              # Engine e SessionLocal
│   ├── models/
│   │   ├── user.py                 # Usuario (admin, atendente)
│   │   ├── conversation.py         # Conversa com contato
│   │   ├── message.py              # Mensagem (inbound/outbound, status)
│   │   ├── runtime_settings.py     # Configuracoes runtime (singleton)
│   │   └── template.py             # Template de mensagens
│   ├── schemas/
│   │   ├── auth.py                 # Login, token, challenge
│   │   ├── user.py                 # CRUD de usuarios
│   │   ├── conversation.py         # Leitura/criacao de conversas
│   │   ├── message.py              # Mensagens, edicao, busca
│   │   ├── export.py               # Exportacao JSON
│   │   ├── admin.py                # Settings de webhook/IA
│   │   ├── ai.py                   # Consulta IA
│   │   ├── template.py             # Templates
│   │   └── upload.py               # Upload
│   ├── services/
│   │   ├── messages.py             # CORE: ingestao, normalizacao, envio
│   │   ├── bootstrap.py            # Admin inicial
│   │   ├── login_challenge.py      # Challenge-response
│   │   ├── runtime_settings.py     # Cache de RuntimeSettings
│   │   ├── schema_maintenance.py   # ALTER TABLEs para novos campos
│   │   ├── conversation_export.py  # Geracao PDF/HTML
│   │   ├── template_service.py     # CRUD de templates
│   │   ├── webhook_sync.py         # Sync env -> banco
│   │   ├── webhook_utils.py        # Token de webhook
│   │   └── media/
│   │       └── media_service.py    # Upload, validacao, delete
│   ├── static/
│   │   └── inbox/
│   │       ├── index.html          # HTML principal
│   │       ├── app.js              # Frontend vanilla JS
│   │       ├── styles.css          # Estilos
│   │       └── img/                # Logos (brasao, STI)
│   └── utils/
│       └── security.py             # JWT, hash (usado pelas rotas)
├── scripts/
│   ├── startup_check.py            # Verificacao FFmpeg e diretorios
│   ├── verify_dependencies.py      # Diagnostico completo
│   ├── check_ffmpeg.py             # Teste detalhado FFmpeg
│   ├── test_webhook.py             # POST manual para webhook
│   ├── debug_download.py           # Teste de download base64
│   ├── migrate_enum.py             # Migracao de enums PostgreSQL
│   ├── init_templates.py           # Templates LGPD/Pesquisa
│   ├── deploy.sh                   # Deploy historico
│   └── test_compression.py         # Teste de compressao de video
├── Dockerfile                      # Imagem Docker (Python 3.12 + FFmpeg)
├── docker-compose.yml              # Compose para EasyPanel
├── requirements.txt                # Dependencias PyPI
├── .env.example                    # Template de variaveis de ambiente
├── AGENTS.md                       # Guia para agentes de IA
└── README.md                       # Este arquivo
```

## Variaveis de Ambiente

Todas as configuracoes ficam em `app/core/config.py`. O `Settings` usa `pydantic-settings`, le `.env`, ignora campos extras e e case-insensitive.

### Variaveis Obrigatorias

| Variavel | Descricao | Exemplo |
| --- | --- | --- |
| `DATABASE_URL` | String de conexao PostgreSQL | `postgresql+psycopg2://user:pass@host:5432/db` |
| `SECRET_KEY` | Chave para assinar JWTs | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |

### Variaveis Recomendadas

| Variavel | Default | Descricao |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | `production` para desabilitar debug logs |
| `DEBUG` | `false` | `true` para logs detalhados |
| `SECRET_KEY` | `change-me-in-production` | Chave JWT - trocar em producao |
| `ADMIN_NAME` | `Admin Principal` | Nome do admin criado no primeiro boot |
| `ADMIN_EMAIL` | `admin@example.com` | Email do admin inicial |
| `CORS_ORIGINS` | `*` | Dominios permitidos (separados por virgula) |
| `PUBLIC_DOMAIN` | (vazio) | Dominio publico para URLs absolutas |

### Uploads e Midia

| Variavel | Default | Descricao |
| --- | --- | --- |
| `UPLOADS_DIR` | `/opt/projetos/chatZapUFPB/uploads` | Diretorio de uploads (deve coincidir com o volume Docker) |
| `MEDIA_MAX_FILE_SIZE` | `26214400` (25MB) | Limite de tamanho por arquivo |
| `MEDIA_ALLOWED_EXTENSIONS` | `.jpg,.jpeg,.png,...` | Extensao permitidas |

### Webhooks (EvolutionAPI / n8n)

| Variavel | Default | Descricao |
| --- | --- | --- |
| `WEBHOOK_TOKEN` | (vazio) | Token de autenticacao inbound |
| `N8N_WEBHOOK_MODE` | `prod` | `test` ou `prod` para selecionar URLs |
| `N8N_INBOUND_WEBHOOK_URL_TEST` | (vazio) | URL inbound em modo test |
| `N8N_INBOUND_WEBHOOK_URL_PROD` | (vazio) | URL inbound em modo prod |
| `N8N_OUTBOUND_WEBHOOK_URL_TEST` | (vazio) | URL outbound em modo test |
| `N8N_OUTBOUND_WEBHOOK_URL_PROD` | (vazio) | URL outbound em modo prod |
| `N8N_OUTBOUND_AUTH_TYPE` | `none` | `none`, `header`, `basic` ou `jwt` |
| `N8N_OUTBOUND_AUTH_HEADER_NAME` | (vazio) | Nome do header (se auth=header) |
| `N8N_OUTBOUND_AUTH_HEADER_VALUE` | (vazio) | Valor do header (se auth=header) |
| `N8N_OUTBOUND_AUTH_BASIC_USERNAME` | (vazio) | Usuario Basic Auth |
| `N8N_OUTBOUND_AUTH_BASIC_PASSWORD` | (vazio) | Senha Basic Auth |
| `N8N_OUTBOUND_AUTH_JWT_TOKEN` | (vazio) | Token Bearer (se auth=jwt) |

### IA

| Variavel | Default | Descricao |
| --- | --- | --- |
| `AI_WEBHOOK_MODE` | `prod` | `test` ou `prod` |
| `AI_WEBHOOK_URL_TEST` | (vazio) | Webhook IA em modo test |
| `AI_WEBHOOK_URL_PROD` | (vazio) | Webhook IA em modo prod |
| `AI_AGENT_WEBHOOK_URL_TEST` | (vazio) | Webhook agente automatico (test) |
| `AI_AGENT_WEBHOOK_URL_PROD` | (vazio) | Webhook agente automatico (prod) |
| `AI_WEBHOOK_USERNAME` | (vazio) | Basic Auth para IA |
| `AI_WEBHOOK_PASSWORD` | (vazio) | Basic Auth para IA |
| `OLLAMA_BASE_URL` | `https://ollama.sti.ufpb.br/` | URL do Ollama local |

> **IMPORTANTE:** As variaveis `N8N_INBOUND_WEBHOOK_URL` e `N8N_OUTBOUND_WEBHOOK_URL` (sem `_TEST`/`_PROD`) NAO sao campos reais do `Settings` e sao ignoradas. Use os campos `_TEST`/`_PROD` e selecione com `N8N_WEBHOOK_MODE`.

## Deploy no EasyPanel

### Passo 1: Configurar o Servico

1. No EasyPanel, crie um novo **Service** do tipo App.
2. Em **Source**, conecte o repositorio GitHub.
3. Nas opcoes de build, selecione **Dockerfile** (nao Nixpacks).
4. Em **Ports**, configure a porta `8000` para HTTP/HTTPS.

### Passo 2: Variaveis de Ambiente

Na aba **Environment**, configure as variaveis obrigatorias e recomendadas (veja secao acima).

### Passo 3: Volumes (MIDIA PERSISTENTE)

Este e o ponto mais critico para que imagens, audios e fotos de perfil nao sejam perdidos entre deploys.

#### Como funcionam os volumes Docker

No Docker, um volume funciona como uma **ponte entre uma pasta do servidor (host) e uma pasta dentro do container**. No arquivo `docker-compose.yml`, foi configurado que a pasta `uploads` do projeto deve aparecer dentro do container em `/opt/projetos/chatZapUFPB/uploads`.

#### EasyPanel - Caminho real dos arquivos

Como o ambiente esta sendo gerenciado pelo EasyPanel, o **caminho fisico real** dos arquivos no servidor nao e exatamente `./uploads`, mas sim um diretorio interno criado pelo proprio EasyPanel:

```
/etc/easypanel/projects/automations-01/whatsapp_fastapi/volumes/uploads
```

Essa pasta do servidor e montada (mount) dentro do container em `/opt/projetos/chatZapUFPB/uploads`.

#### Por que `/uploads` nao existe

Ao tentar acessar `/uploads` dentro do container, ocorre erro "No such file or directory". Isso porque **o caminho correto e `/opt/projetos/chatZapUFPB/uploads`**, nao `/uploads`.

#### Resumo do fluxo

```
Servidor (host)                                    Container
─────────────────────────────────────────────────────────────
/etc/easypanel/projects/.../uploads  ──mount──>  /opt/projetos/chatZapUFPB/uploads
```

Qualquer arquivo gravado nessa pasta dentro do container e armazenado fisicamente na pasta correspondente do servidor gerenciada pelo EasyPanel, permitindo que os dados permanecam preservados mesmo que o container seja recriado ou atualizado.

#### Configuracao no EasyPanel

Na aba **Storage / Volumes**:

| Tipo | Caminho | Nome do Volume |
| --- | --- | --- |
| Volume | `/opt/projetos/chatZapUFPB/uploads` | `uploads_data` |
| Volume | `/app/runtime` | `runtime_data` |

> **NUNCA** crie o volume com caminho `/uploads`. Use sempre `/opt/projetos/chatZapUFPB/uploads`.

### Passo 4: Deploy

Clique em **Deploy**. O `startup_check.py` sera executado automaticamente, verificando FFmpeg e diretorios, e o banco de dados sera criado/atualizado automaticamente.

## Deploy Local (Docker Compose)

```bash
git clone <repo>
cp .env.example .env
# Edite .env com suas configuracoes
docker compose up -d --build
```

- Frontend: `http://localhost:8000/inbox`
- API Docs: `http://localhost:8000/api/v1/docs`
- Health: `http://localhost:8000/health`

## Deploy Local (Desenvolvimento)

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Regras de Negocio

### Numero Oficial (Anti-Loop)

O numero **+558332167336** esta hardcoded em `app/services/messages.py` para evitar loops com o proprio bot. Webhooks com esse numero como contato sao ignorados.

Se o numero oficial mudar, altere na funcao `ingest_inbound_message()`:

```python
if contact_phone == "+55NOVO_NUMERO":
    return None
```

### Normalizacao de Telefone

A funcao `_normalize_phone()` em `app/services/messages.py`:
- Remove tudo que nao for digito
- Adiciona `55` automaticamente para telefones brasileiros de 10/11 digitos
- Remove o 9o digito para DDD > 28 (regra JID WhatsApp)
- Retorna no formato `+<digitos>`

### Deduplicacao

- **Por `external_message_id`**: evita duplicatas no banco
- **Por texto + janela de 2 minutos**: evita duplicatas de outbound sem ID externo
- **Outbound universal**: qualquer mensagem recente sem `external_message_id` na mesma conversa e candidata a match (usa comparacao Python para lidar com `NULL`)

### Status de Entrega

Mapping de status da EvolutionAPI (string ou numerico):

| EvolutionAPI | Sistema |
| --- | --- |
| `SERVER_ACK`, `1` | `SENT` |
| `DELIVERY_ACK`, `2` | `DELIVERED` |
| `PLAYED`, `3` | `READ` |
| `READ`, `4` | `READ` |
| `ERROR`, `5` | `FAILED` |
| `SENDING`, `6` | `QUEUED` |
| `PROGRESS`, `7` | `SENT` |

### Edicao de Mensagens

- **Atendente edita**: PATCH `/conversations/{id}/messages/{id}/edit` com `{ "text_content": "novo texto" }`. Envia `action: "edit_message"` para n8n.
- **WhatsApp edita**: `messages.update` com `data.update.message.editedMessage` - mensagem existente e atualizada (nao cria duplicata).
- **secretEncryptedMessage**: EvolutionAPI envia evento separado quando WhatsApp edita - marca como editado sem criar duplicata.

### Citacao de Mensagens (Quotes)

Quando uma mensagem citada chega via webhook, o `quoted_message_text` e `quoted_message_sender` sao extraidos do `contextInfo` (funciona para imageMessage, videoMessage, documentMessage, audioMessage).

### Mensagens Nao Lidas

- Campo `is_read` na tabela `messages`
- Endpoint `POST /conversations/{id}/messages/read` marca todas como lidas
- Frontend chama ao abrir conversa
- CSS `.message-unread` destaca com borda diferenciada

### Fotos de perfil

- Download via `_download_profile_picture()` em `app/services/messages.py`
- Armazenadas localmente com prefixo `profile_`
- Frontend usa `onerror` no `<img>` para fallback com iniciais

## API - Resumo das Rotas

Todas as rotas usam prefixo `/api/v1`, exceto health e webhooks publicos.

### Autenticacao

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/auth/challenge` | Publico | Desafio anti-bots |
| `POST` | `/auth/login` | Publico | Login com challenge |
| `GET` | `/auth/me` | JWT | Dados do usuario logado |
| `POST` | `/auth/change-password` | JWT | Troca de senha |
| `POST` | `/auth/logout` | JWT | Logout |

### Conversas e Mensagens

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/conversations` | JWT | Lista conversas com mensagens |
| `POST` | `/conversations` | JWT | Cria conversa manual |
| `GET` | `/conversations/search/messages?q=` | JWT | Busca em mensagens |
| `GET` | `/conversations/{id}/messages` | JWT | Lista mensagens |
| `POST` | `/conversations/{id}/messages` | JWT | Envia mensagem outbound |
| `PATCH` | `/conversations/{id}/messages/{id}/edit` | JWT | Edita mensagem outbound |
| `POST` | `/conversations/{id}/messages/{id}/revoke` | JWT | Revoga mensagem |
| `POST` | `/conversations/{id}/messages/read` | JWT | Marca como lida |
| `DELETE` | `/conversations/{id}/messages/all` | Admin | Apaga todas da conversa |
| `DELETE` | `/conversations/messages/all` | Admin | Apaga tudo |
| `GET` | `/conversations/{id}/export?export_date=` | JWT | Export JSON |
| `GET` | `/conversations/{id}/export/pdf?export_date=` | JWT | Export PDF |

### Webhooks (Publicos - sem auth JWT)

| Metodo | Rota | Descricao |
| --- | --- | --- |
| `POST` | `/webhook` | Webhook inbound (EvolutionAPI/n8n) |
| `POST` | `/api/inbox` | Webhook inbound (alternativo) |
| `POST` | `/webhooks/evolution` | Webhook versionado |

Headers aceitos para token: `x-webhook-token`, `x-token`, `Authorization: Bearer`, query `?token=`

### Admin

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/admin/webhook-settings` | Admin | Config de webhooks |
| `PUT` | `/admin/webhook-settings` | Admin | Atualiza webhooks |
| `GET` | `/admin/ai-settings` | Admin | Config de IA |
| `PUT` | `/admin/ai-settings` | Admin | Atualiza IA |
| `DELETE` | `/admin/cleanup/messages` | Admin | Apaga todas mensagens |
| `DELETE` | `/admin/cleanup/uploads` | Admin | Apaga todas midias |
| `DELETE` | `/admin/cleanup/contacts` | Admin | Apaga todas conversas |

### Templates

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/templates` | JWT | Lista templates ativos |
| `POST` | `/templates` | Admin | Cria template |
| `PUT` | `/templates/{id}` | Admin | Atualiza template |
| `DELETE` | `/templates/{id}` | Admin | Remove template |
| `POST` | `/templates/initialize` | Admin | Cria templates LGPD/Pesquisa |

### Upload

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `POST` | `/uploads/media` | JWT | Upload de midia (rejeita video) |
| `GET` | `/uploads/media/{filename}` | JWT | Info do arquivo |
| `DELETE` | `/uploads/media/{filename}` | JWT | Remove arquivo |

### IA

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `POST` | `/ai/ask` | JWT | Pergunta para IA |
| `GET` | `/ai/fetch-models?provider=` | JWT | Lista modelos |

## Frontend

O frontend e vanilla JS servido em `/inbox`. Nao requer build step.

### Arquivos

- `app/static/inbox/index.html` - HTML principal
- `app/static/inbox/app.js` - Logica da aplicacao (~3000 linhas)
- `app/static/inbox/styles.css` - Estilos (~2800 linhas)

### Funcionalidades do Frontend

- **Login com challenge-response** - anti-bots
- **Sidebar de conversas** - ordenada por ultima mensagem
- **Chat** - mensagens com suporte a texto, imagem, audio, documento
- **Composer** - campo de texto com upload de midia, gravacao de audio, templates
- **Edicao inline** - botao de editar em mensagens outbound de texto
- **Revogacao** - botao de apagar para todos
- **Mensagens nao lidas** - indicador visual
- **Citacao de mensagens** - visualizacao de mensagem respondida
- **Visualizacao de midia** - modal para imagens em tamanho completo
- **Preview de arquivos** - thumbnail ao lado do botao de enviar
- **Templates** - modal de selecao com trigger por `/`
- **Exportacao** - PDF e HTML
- **Config de IA** - toggle de agente e selecao de provider

### Objeto `els`

O frontend mapeia todos os elementos DOM por ID no objeto `els`. Qualquer alteracao em IDs no HTML deve ser refletida no JS.

## Arquitetura

### Padroes Utilizados

- **Factory Pattern** - `app/core/app_factory.py` cria e configura o FastAPI
- **Repository Pattern** - modelos SQLAlchemy como camada de acesso a dados
- **Singleton** - `RuntimeSettings` (id=1) com cache em memoria
- **Challenge-Response** - login anti-bots com desafio temporario

### Ciclo de Vida da Aplicacao

1. `create_application()` instancia `ApplicationFactory`
2. `lifespan`:
   - Aguarda banco (`SELECT 1` com retry)
   - `Base.metadata.create_all()` - cria tabelas
   - `ensure_schema_compatibility()` - ADD COLUMN IF NOT EXISTS
   - `ensure_initial_admin_user()` - cria admin se nao existir
   - `get_or_create_runtime_settings()` - singleton
   - `sync_webhook_urls_on_startup()` - env -> banco
   - Cria diretorio de midia

### Fluxo de Mensagens

**Inbound (WhatsApp -> Sistema):**
1. EvolutionAPI/envia webhook para `/webhook` ou `/api/inbox`
2. `ingest_inbound_message()` normaliza telefone, detecta tipo, extrai midia
3. Cria `Message` com `direction=inbound`, `delivery_status=received`
4. Atualiza `conversation.last_message_at`
5. Opcionalmente encaminha para agente IA (background task)

**Outbound (Sistema -> WhatsApp):**
1. Atendente envia via frontend
2. `create_outbound_message()` cria `Message` com `direction=outbound`, `delivery_status=queued`
3. POST para n8n com payload (to, text, media, attendant)
4. n8n reencaminha para EvolutionAPI
5. Webhook de status atualiza `delivery_status`

## Comandos Uteis

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

# Verificar health
curl http://localhost:8000/health

# Testar webhook
python scripts/test_webhook.py
```

## Armilhas Conhecidas

1. `N8N_INBOUND_WEBHOOK_URL` e `N8N_OUTBOUND_WEBHOOK_URL` (sem `_TEST`/`_PROD`) NAO sao campos reais e sao ignorados.
2. O numero `+558332167336` esta hardcoded como numero do bot - nao esqueca de ajustar se mudar.
3. `app/api/routes/uploads.py` e rota legada nao registrada - use `uploads_v2.py`.
4. `app/core/security.py` e `app/utils/security.py` geram formatos JWT diferentes - as rotas atuais usam `app/utils/security.py`.
5. `RuntimeSettings` cacheia objeto expunged - para escrita, carregue na sessao atual e invalide cache.
6. `MediaService.get_media_info()` referencia `video_converter` nao importado - caminho so e atingido com video no storage.
7. `app/static/inbox/app.js` declara `escapeHtml` duas vezes - a segunda sobrescreve.
8. `app/static/inbox/app.js` referencia `recordPreview` mas `index.html` nao tem esse ID.
9. `styles.css` tem bloco de IA duplicado e trecho com `transform: scale(1)` solto dentro de `@media`.
10. Pre-existente: `styles.css` tem erro de chave CSS nao fechada por volta da linha 2788.

## Tecnologias

- **Backend:** FastAPI 0.128.3, SQLAlchemy 2.0.40, psycopg2-binary 2.9.10
- **Auth:** python-jose 3.3.0, passlib 1.7.4, bcrypt 4.0.1
- **Config:** pydantic-settings 2.8.1
- **HTTP:** httpx 0.28.1
- **Report:** reportlab 4.4.1
- **Frontend:** Vanilla JS (sem framework)
- **Banco:** PostgreSQL (via SQLAlchemy)
- **WhatsApp:** EvolutionAPI v2.3.7 + n8n
- **Container:** Docker (Python 3.12-slim + FFmpeg)
- **Deploy:** EasyPanel

## Licenciamento

Projeto interno da UFPB - Setor de Tecnologia da Informacao (STI).
