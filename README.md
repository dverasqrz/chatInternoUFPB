# WhatsApp Multiatendente Institucional UFPB

Aplicação em Python (FastAPI) com Docker Compose e PostgreSQL em containers separados, com interface web estilo inbox para operação multiatendente.

## O que já está implementado

- Container `app` (FastAPI) + container `db` (PostgreSQL).
- Interface web para atendentes em `/inbox`.
- Recebimento de mensagens por webhook do n8n/EvolutionAPI.
- Suporte para mensagens `text`, `audio`, `video` e `image`.
- Upload de imagem local pela inbox (arquivo da máquina).
- Gravação de áudio e vídeo na inbox (com pedido de autorização do navegador).
- Mensagem amigável quando não houver microfone/webcam disponível.
- Charada matemática no login para reduzir tentativas automatizadas.
- Desconexão por inatividade de 7 dias sem interação do funcionário.
- Conversas por contato (um único número WhatsApp, vários atendentes).
- Registro de quem respondeu cada mensagem (`attendant_id`, `sender_name`).
- Autenticação com JWT.
- Auditoria de sessão por usuário: último login e último logout.
- Exportação por intervalo da conversa em HTML e PDF (com identificação de cliente e autor da mensagem).
- Exportação com imagem incorporada (quando disponível localmente), inclusive no PDF.
- Usuário inicial automático:
  - Nome: `Diego Veras`
  - E-mail: `diego.veras@gmail.com`
  - Senha: gerada na primeira inicialização.
- Cadastro de novos usuários apenas por admin.
- Todo usuário novo entra com `must_change_password=true` e precisa trocar a senha no primeiro acesso.

## Estrutura

```text
app/
  api/
    deps.py
    routes/
      auth.py
      conversations.py
      health.py
      users.py
      webhook.py
  core/config.py
  db/
    base.py
    session.py
  models/
    conversation.py
    message.py
    user.py
  schemas/
    auth.py
    conversation.py
    message.py
    user.py
  services/
    bootstrap.py
    messages.py
    runtime_settings.py
  utils/security.py
  main.py
```

## Subir o projeto

1. Revise o arquivo `.env`.
2. Suba os containers:

```bash
docker compose up -d --build
```

3. Abra:
   - Inbox web: `http://localhost:8000/inbox`
   - API: `http://localhost:8000`
   - Swagger: `http://localhost:8000/docs`

## Senha inicial do Diego

Na primeira execução, a senha gerada é salva em:

```text
runtime/admin_bootstrap.txt
```

Depois, entre na inbox `http://localhost:8000/inbox` e faça login com este e-mail/senha.

## Primeiros passos (ordem recomendada)

1. Configure o `.env`:
   - Troque `SECRET_KEY`.
   - Defina `WEBHOOK_TOKEN` (recomendado).
   - Defina `N8N_OUTBOUND_WEBHOOK_URL`.
   - Defina `N8N_OUTBOUND_AUTH_TYPE` e as credenciais de saída correspondentes.
2. Suba a stack:
   - `docker compose up -d --build`
3. Pegue a senha inicial do Diego:
   - arquivo `runtime/admin_bootstrap.txt`
4. Faça login no navegador:
   - `http://localhost:8000/inbox`
   - botão `Senha` permite alterar a senha a qualquer momento.
   - login exige resposta de uma charada matemática simples.
   - sessão expira por inatividade de 7 dias sem interação do funcionário.
5. Com o usuário Diego, cadastre os atendentes:
   - pela própria área admin da inbox (ou API `POST /api/v1/users`).
6. Cada atendente entra na inbox e, no primeiro login, troca a senha obrigatoriamente.
7. Na inbox, seção `Admin: Usuários`, o administrador pode:
   - adicionar usuário,
   - excluir usuário,
   - resetar senha (forçando troca no próximo login),
   - ativar/desativar usuário,
   - listar usuários ativos,
   - acompanhar último login/logout (exibição em horário de Recife).
8. Configure o n8n para enviar o webhook de entrada da EvolutionAPI para:
   - `POST /api/v1/webhooks/evolution`
   - Header opcional: `x-webhook-token: <WEBHOOK_TOKEN>`
9. Operação diária:
   - atendente seleciona conversa no painel esquerdo e responde no painel principal.
   - imagem: selecione `Imagem` e use `Enviar imagem local`.
   - áudio: selecione `Áudio` e use `Gravar áudio`.
   - vídeo: selecione `Vídeo` e use `Gravar vídeo`.
   - para exportar uma conversa do dia, use `Exportar dia desta mensagem` em qualquer bolha e escolha intervalo (00:00-23:59 por padrão, editável), perfil do cliente e formato HTML/PDF.
   - perfis disponíveis: `Aluno`, `Professor`, `Funcionário`, `Externo`, `Ex-aluno`, `Múltiplos`, `Indefinido` (padrão).

## Segurança mínima recomendada

- Trocar `SECRET_KEY` no `.env`.
- Definir `WEBHOOK_TOKEN` e enviar no header `x-webhook-token`.
- Para saída app -> n8n, usar autenticação no webhook de saída (preferencialmente `Header Auth` com token forte e rotativo).
- Rodar atrás de reverse proxy HTTPS.

## Configuração n8n (Webhook + HTTP Request)

Fluxo n8n sugerido:

```text
Webhook (EvolutionAPI)
  -> Function (normalização)
  -> HTTP Request
  -> FastAPI (/webhook)
```

### Endpoint para usar no HTTP Request do n8n

- Recomendado: `POST https://SEU_NGROK/webhook`
- Alias aceito: `POST https://SEU_NGROK/api/inbox`
- Endpoint legado ainda válido: `POST https://SEU_NGROK/api/v1/webhooks/evolution`

Não use `https://SEU_NGROK/inbox` para webhook de entrada, porque `/inbox` é a interface HTML.

### n8n -> app (entrada)

No `.env`, mantenha a URL de entrada operacional registrada:

- `N8N_INBOUND_WEBHOOK_URL` (ex.: `https://workflow.vqautomacao.com.br/webhook/entrada_chat_UFPB`)

Importante:

- Use URL de produção do n8n (`/webhook/...`) para operação contínua.
- A URL de teste (`/webhook-test/...`) exige clicar em `Execute workflow` e não é estável para produção.

Se token estiver configurado no app, envie:

```text
x-token: ufpb_secret
```

Também é aceito:

```text
x-webhook-token: ufpb_secret
```

No nó `HTTP Request` do n8n (que chama seu app):

- `Method`: `POST`
- `URL`: `https://SEU_NGROK/webhook`
- `Authentication`: `None` (o controle será pelo header do token)
- `Header`: `x-token: <TOKEN_ENTRADA_CONFIGURADO_NO_APP>`

### app -> n8n (saída)

Configure no `.env` da aplicação:

- `N8N_OUTBOUND_WEBHOOK_URL`: URL do Webhook Trigger do n8n (ex.: `https://workflow.vqautomacao.com.br/webhook/saida_chat_UFPB`)
- `N8N_OUTBOUND_AUTH_TYPE`: `header` (recomendado), `basic`, `jwt` ou `none`
- Se `header`: `N8N_OUTBOUND_AUTH_HEADER_NAME` e `N8N_OUTBOUND_AUTH_HEADER_VALUE`
- Se `basic`: `N8N_OUTBOUND_AUTH_BASIC_USERNAME` e `N8N_OUTBOUND_AUTH_BASIC_PASSWORD`
- Se `jwt`: `N8N_OUTBOUND_AUTH_JWT_TOKEN`

No Webhook Trigger do n8n, configure o mesmo modo selecionado no app:

- Se usar `Header Auth`: `Authentication = Header Auth`, mesmo header e mesmo valor.
- Se usar `Basic Auth`: `Authentication = Basic Auth`, mesmo usuário/senha.
- Se usar `JWT Auth`: `Authentication = Header Auth` com `Authorization: Bearer <jwt>`.

### Corpo JSON mínimo aceito

```json
{
  "name": "Aluno João",
  "phone": "5583999999999",
  "type": "text",
  "message": "Olá"
}
```
