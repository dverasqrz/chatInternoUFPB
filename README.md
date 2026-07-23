# UFPB Chat System

Sistema de chat institucional da UFPB com integracao WhatsApp, gerenciamento de usuarios e recursos avancados.

## Visao Geral

Aplicacao FastAPI para atendimento multiatendente via WhatsApp. Frontend vanilla JS servido pelo proprio FastAPI, banco PostgreSQL via SQLAlchemy, integracao com EvolutionAPI/n8n para envio/recebimento de mensagens, upload de midia, templates de mensagens, exportacao de conversas (PDF/HTML) e recursos de IA.

**Versao atual:** 2.0.0  
**Stack principal:** Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vanilla JS  
**Infraestrutura:** Docker + EasyPanel  

## Funcionalidades

### Chat e Mensagens
- **Chat em tempo real** com interface moderna e responsiva
- **Integracao WhatsApp** via EvolutionAPI v2.3.7 + n8n (webhooks inbound/outbound)
- **Multiatendente** com autenticacao por JWT e controle de permissoes
- **Envio por Enter** - pressionar Enter envia a mensagem; Ctrl+Enter ou Shift+Enter cria nova linha
- **Edicao de mensagens** - atendentes editam texto outbound via botao inline; edicoes do WhatsApp sao refletidas
- **Mensagens citadas (quotes)** - contexto de mensagem respondida preservado com botao de resposta
- **Mensagens nao lidas** - indicador visual por conversa com badge verde e animacao
- **Ferramenta externa** - mensagens de ferramentas externas (Chatwoot, WhatsApp original) identificadas como "Ferramenta externa"

### Midia e Conteudo
- **Upload de midia** - imagens, audios, documentos (video suportado via webhook)
- **Stickers** - suporte completo a stickers WhatsApp (normalizados como imagem)
- **Download de midia** - baixa automatica de imagens/audios do WhatsApp (base64 ou CDN)
- **Zoom de imagens** - modal com zoom via scroll do mouse, pan ao arrastar, duplo clique para zoom 2.5x
- **Thumbnails de documentos** - preview antes de enviar
- **Fotos de perfil** - download e armazenamento local de avatares de contatos
- **Legendas** - suporte a caption em imagens, videos e documentos

### Organizacao
- **Templates de mensagens** - 7 templates pre-configurados (LGPD, Pesquisa, Contatos, Chamado, Identidade, Permissoes)
- **Busca** - pesquisa em mensagens incluindo legendas de midia
- **Exportacao** - PDF (ReportLab) e HTML com range de datas, nome do telefone e autor corrigido
- **Limpeza automatica** - remocao de conversas vazias no startup

### IA e Integracao
- **Sistema de IA** - consulta via n8n com toggle de agente automatico
- **Normalizacao de midia** - stickers e outros tipos sao normalizados para compatibilidade com n8n

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
│   │   ├── message.py              # Mensagem (inbound/outbound, status, tipo)
│   │   ├── runtime_settings.py     # Configuracoes runtime (singleton)
│   │   └── template.py             # Template de mensagens
│   ├── schemas/
│   │   ├── auth.py                 # Login, token, challenge
│   │   ├── user.py                 # CRUD de usuarios
│   │   ├── conversation.py         # Leitura/criacao de conversas (com unread_count)
│   │   ├── message.py              # Mensagens, edicao, busca, quoted_message_*
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
│   │   ├── conversation_export.py  # Geracao PDF/HTML (com attenant_id)
│   │   ├── template_service.py     # CRUD de templates
│   │   ├── webhook_sync.py         # Sync env -> banco
│   │   ├── webhook_utils.py        # Token de webhook
│   │   └── media/
│   │       └── media_service.py    # Upload, validacao, delete
│   ├── static/
│   │   └── inbox/
│   │       ├── index.html          # HTML principal
│   │       ├── app.js              # Frontend vanilla JS
│   │       ├── styles.css          # Estilos (com visual overhaul)
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
│   ├── fix_contact_names.py        # Corrige nomes "Voce" com nomes reais
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

### Resolucao LID

Quando `remoteJid` contem `@lid`, o sistema faz fallback:
1. `remoteJidAlt` (telefone alternativo)
2. `sender` (remitente do payload)
3. `payload.sender` (nivel raiz)

### Deduplicacao

- **Por `external_message_id`**: evita duplicatas no banco
- **Por texto + janela de 2 minutos**: evita duplicatas de outbound sem ID externo
- **Por tipo de midia**: mensagens recentes sem `external_message_id` sao candidatas a match
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
- Frontend chama ao abrir conversa e ao enviar resposta
- CSS `.message-unread` destaca com gradiente verde e animacao pulsante
- Badge verde na sidebar com contagem de nao lidas
- Ao enviar mensagem, todas as inbound sao marcadas como lidas automaticamente

### Identificacao de Atendente

O sistema distingue quem enviou a mensagem:

- **Funcionario logado no FastAPI**: `attendant_id` preenchido → nome real do funcionario
- **Ferramenta externa** (Chatwoot, WhatsApp original, n8n): `attendant_id` NULL → "Ferramenta externa"

Isso e automatico porque `attendant_id` so e preenchido em `create_outbound_message()`, quando o usuario esta logado.

### Fotos de perfil

- Download via `_download_profile_picture()` em `app/services/messages.py`
- Armazenadas localmente com prefixo `profile_`
- Frontend usa `onerror` no `<img>` para fallback com iniciais

### Templates de Mensagens

Sistema inicializa com 7 templates automaticos:
1. LGPD Bom dia
2. LGPD Boa tarde
3. Pesquisa de Satisfacao
4. Contatos Secretaria STI
5. Abertura de Chamado
6. Confirmacao de Identidade
7. Permissoes SIPAC-PROTOCOLO

Templates sao recriados a cada startup (drops antigos, recria).

### Limpeza de Conversas Vazias

No startup, `_cleanup_invalid_contacts()` remove conversas que nao possuem nenhuma mensagem associada.

### Preventacao de Conversas Vazias

Eventos `contacts.upsert` e `contacts.update` NAO criam conversas vazias - apenas atualizam conversas existentes.

### Exportacao

- **Range de datas**: endpoint aceita `start_date` e `end_date` para exportacao multi-dia
- **Nomes no arquivo**: PDF/HTML usam formato `{telefone}_{DD_MM_YYYY}.pdf`; para multi-dia: `{telefone}_{DD_MM_YYYY}-{DD_MM_YYYY}.pdf`
- **Autor correto**: exportacao usa `attendant_id` para buscar nome real do atendente
- **Legendas**: exportacao inclui `media_caption` antes de `text_content`
- **Toast verde**: exportacao concluida mostra toast de sucesso verde

### Busca de Mensagens

Endpoint `GET /conversations/search/messages?q=` busca em:
- `text_content` (texto da mensagem)
- `media_caption` (legenda de midia)

### Suporte a Stickers

- Enum `MessageType.STICKER` adicionado ao sistema
- `stickerMessage` normalizado para `imageMessage` (compatibilidade n8n)
- Download de base64 a partir de `stickerMessage`
- Frontend renderiza como imagem com estilo `.message-sticker`
- Migracao PostgreSQL: `ALTER TYPE message_type ADD VALUE IF NOT EXISTS 'sticker'`

### Download de Midia WhatsApp

`_download_whatsapp_media()` prioriza:
1. `imageMessage.base64` ou `stickerMessage.base64`
2. `message.base64` (root level)
3. `data.base64` (data level)
4. Download da CDN via URL

### Zoom de Imagens

Modal de visualizacao de imagens suporta:
- **Scroll do mouse**: zoom in/out (0.5x a 10x)
- **Arrastar**: pan pela imagem quando zoom > 1
- **Duplo clique**: zoom 2.5x no ponto clicado ou volta ao normal
- **X ou clique fora**: fecha o modal

### Atalhos de Teclado

- **Enter**: envia a mensagem
- **Ctrl+Enter** ou **Shift+Enter**: nova linha (paragrafo)

### Scroll Automatico

Ao enviar mensagem, a tela rola automaticamente para o final da conversa.

### Normalizacao de Nomes de Contato

Nomes placeholder ("Voce", "Voce", "Eu") sao filtrados:
- `_get_or_create_conversation()`: nao usa nomes placeholder
- `ingest_inbound_message()`: ignora nomes placeholder

Script `scripts/fix_contact_names.py` corrige contatos existentes extraindo nomes reais do `pushName` das mensagens inbound.

## API - Resumo das Rotas

Todas as rotas usam prefixo `/api/v1`, exceto health e webhooks publicos.

### Autenticacao

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/auth/challenge` | Publico | Desafio anti-bots |
| `POST` | `/auth/login` | Publico | Login com challenge |
| `GET` | `/auth/me` | JWT | Dados do usuario logado |
| `GET` | `/auth/config` | Publico | Config publica (domain, debug) |
| `POST` | `/auth/change-password` | JWT | Troca de senha |
| `POST` | `/auth/logout` | JWT | Logout |

### Conversas e Mensagens

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `GET` | `/conversations` | JWT | Lista conversas com unread_count |
| `POST` | `/conversations` | JWT | Cria conversa manual |
| `GET` | `/conversations/contacts/all` | JWT | Todos os contatos |
| `GET` | `/conversations/search/messages?q=` | JWT | Busca em mensagens (min 3 chars) |
| `GET` | `/conversations/{id}/messages` | JWT | Lista mensagens |
| `POST` | `/conversations/{id}/messages` | JWT | Envia mensagem (com quote) |
| `PATCH` | `/conversations/{id}/messages/{id}/edit` | JWT | Edita mensagem outbound |
| `POST` | `/conversations/{id}/messages/{id}/revoke` | JWT | Revoga mensagem |
| `POST` | `/conversations/{id}/messages/read` | JWT | Marca como lida |
| `POST` | `/conversations/{id}/messages/delete-selected` | Admin | Delete em lote |
| `DELETE` | `/conversations/{id}/messages/all` | Admin | Apaga todas da conversa |
| `DELETE` | `/conversations/messages/all` | Admin | Apaga tudo |
| `GET` | `/conversations/{id}/export` | JWT | Export JSON |
| `GET` | `/conversations/{id}/export/pdf` | JWT | Export PDF |

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
| `GET` | `/templates/{id}` | JWT | Template especifico |
| `GET` | `/templates/category/{category}` | JWT | Por categoria |
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
| `POST` | `/uploads/cleanup?days=30` | Admin | Limpa arquivos antigos |

### IA

| Metodo | Rota | Auth | Descricao |
| --- | --- | --- | --- |
| `POST` | `/ai/ask` | JWT | Pergunta para IA |
| `GET` | `/ai/fetch-models?provider=` | JWT | Lista modelos |

## Frontend

O frontend e vanilla JS servido em `/inbox`. Nao requer build step.

### Arquivos

- `app/static/inbox/index.html` - HTML principal
- `app/static/inbox/app.js` - Logica da aplicacao (~3700 linhas)
- `app/static/inbox/styles.css` - Estilos (~3100 linhas)

### Funcionalidades do Frontend

- **Login com challenge-response** - anti-bots
- **Sidebar de conversas** - ordenada por ultima mensagem com badge de nao lidas
- **Chat** - mensagens com suporte a texto, imagem, audio, video, documento, sticker
- **Composer** - campo de texto com upload de midia, gravacao de audio, templates
- **Envio por Enter** - Ctrl+Enter ou Shift+Enter para nova linha
- **Edicao inline** - botao de editar em mensagens outbound de texto
- **Revogacao** - botao de apagar para todos
- **Citacao** - botao de responder com preview da mensagem original
- **Mensagens nao lidas** - indicador visual com gradiente verde
- **Identificacao** - nome do funcionario ou "Ferramenta externa"
- **Zoom de imagens** - modal com zoom via mouse wheel e pan
- **Preview de arquivos** - thumbnail apos upload
- **Templates** - modal de selecao com trigger por `/`
- **Exportacao** - modal com range de datas para PDF/HTML
- **Config de IA** - toggle de agente e selecao de provider
- **Scroll automatico** - rola para o final apos enviar mensagem

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
   - `_initialize_system_templates()` - 7 templates LGPD/Pesquisa
   - `_cleanup_invalid_contacts()` - remove conversas vazias
   - `sync_webhook_urls_on_startup()` - env -> banco
   - Cria diretorio de midia

### Fluxo de Mensagens

**Inbound (WhatsApp -> Sistema):**
1. EvolutionAPI envia webhook para `/webhook` ou `/api/inbox`
2. `ingest_inbound_message()` normaliza telefone, detecta tipo, extrai midia
3. Baixa midia localmente (base64 ou CDN)
4. Cria `Message` com `direction=inbound`, `delivery_status=received`
5. Atualiza `conversation.last_message_at`
6. Opcionalmente encaminha para agente IA (background task)

**Outbound (Sistema -> WhatsApp):**
1. Atendente envia via frontend (logado)
2. `create_outbound_message()` cria `Message` com `attendant_id`, `sender_name`, `delivery_status=queued`
3. POST para n8n com payload (to, text, media, attendant)
4. n8n reencaminha para EvolutionAPI
5. Webhook de status atualiza `delivery_status`

**Outbound Externo (Chatwoot/WhatsApp/n8n -> Sistema):**
1. Webhook chega com `event=send.message` e `fromMe=true`
2. `ingest_inbound_message()` cria `Message` com `attendant_id=NULL`
3. Frontend exibe como "Ferramenta externa"

### Migracao de Schema

Nao usa Alembic. Em vez disso, `ensure_schema_compatibility()` roda `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para cada campo novo. Seguro para rodar repetidamente.

Campos migrados:
- `users`: `last_login_at`, `last_logout_at`, `last_interaction_at`
- `runtime_settings`: `outbound_auth_*`, `ai_provider`, `ai_api_key`, `ai_base_url`, `ai_model`
- `conversations`: `profile_picture_url`
- `messages`: `updated_at`, `is_edited`, `is_read`, `quoted_message_text`, `quoted_message_sender`, `quoted_message_id`, `quoted_message_participant`
- `message_type` enum: valor `sticker` adicionado

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

# Corrigir nomes de contatos
python scripts/fix_contact_names.py
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
11. `send.message` e um evento da n8n/EvolutionAPI que nao e `messages.upsert` - o sistema trata como mensagem regular.

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
