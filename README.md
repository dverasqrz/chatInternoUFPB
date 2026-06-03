# UFPB Chat System

Sistema de chat institucional da UFPB com integração WhatsApp, gerenciamento de usuários e recursos avançados.

## Features

- **Chat em tempo real** com interface moderna e fluida
- **Integração WhatsApp** avançada via EvolutionAPI/n8n
- **Gerenciamento de usuários** com diferentes níveis de permissões
- **Upload de mídia** suportando imagens, documentos, áudios e vídeos nativamente
- **Sistema administrativo** completo para moderação e controle
- **Políticas de limpeza automática** focadas em segurança de dados
- **Interface responsiva** compatível com múltiplos dispositivos
- **Sistema Dinâmico de Templates** para o uso de Mensagens Prontas
- **LGPD Integrada** para solicitar consentimento com um clique
- **Arquitetura Resiliente** com tratamentos avançados de falha e desconexão

## 📁 Estrutura do Projeto

```text
chatZapUFPB/
├── app/                    # Código-fonte da aplicação FastAPI
│   ├── api/                # Rotas organizadas por domínio
│   ├── core/               # Padrões de Projeto (Factory, Exceptions, Logging)
│   ├── db/                 # Sessão do PostgreSQL e Base Models
│   ├── models/             # Esquemas de Banco de Dados SQLAlchemy
│   ├── schemas/            # Contratos de API Pydantic
│   ├── services/           # Lógica de Negócios e Regras Isoladas
│   ├── static/             # Frontend e Interface (Vanilla JS)
│   └── utils/              # Ferramentas auxiliares
├── .dockerignore           # Arquivo restritivo para builds performáticas
├── Dockerfile              # Imagem pronta para Produção (com FFmpeg)
├── docker-compose.yml      # Ambiente completo (App + DB)
└── requirements.txt        # Dependências PyPI do Backend
```

## 🚀 Implantação Rápida no EasyPanel

O projeto foi totalmente otimizado para deploy *zero-config* em painéis de hospedagem modernos como o **EasyPanel**. Ele usa um `Dockerfile` customizado para já incluir o `ffmpeg` nativamente, garantindo processamento de mídias de vídeo e áudio sem instalar dependências externas no painel.

### Passo 1: Configurar no Painel
1. Dentro do seu servidor do **EasyPanel**, crie um novo **Service** do app.
2. Em **Source**, conecte este Repositório do GitHub.
3. Nas opções de build, selecione a opção **Dockerfile** em vez de Nixpacks se questionado (mesmo se deixar em *Auto*, ele preferirá o Dockerfile que já preparamos na raiz do projeto - o que é o correto).
4. Em **Ports**, certifique-se de que a porta principal esteja redirecionada de **`8000`** para HTTP/HTTPS `443` ou `80` (O FastAPI da aplicação expõe a porta `8000`).

### Passo 2: Configurar Variáveis de Ambiente
No Easypanel, navegue até a aba **Environment** da sua aplicação. Preste atenção especial em definir o ambiente para Produção, para inibir debug logs gigantescos.
```env
# Banco de Dados (Use a configuração do Postgres previamente criado ou externo)
DATABASE_URL=postgresql+psycopg2://user:password@seu_host_db:5432/dbname

# Segurança Básica
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=sua-chave-secreta-muito-segura-aqui
ACCESS_TOKEN_EXPIRE_MINUTES=30

# URLs e CORS (Ajuste para o seu domínio do EasyPanel)
CORS_ORIGINS=https://seu-dominio-chat.com
PUBLIC_DOMAIN=https://seu-dominio-chat.com

# Webhooks da Evolution API
N8N_INBOUND_WEBHOOK_URL=https://n8n.seu.dominio/webhook/event/inbound
WEBHOOK_TOKEN=token-de-seguranca

# Setup do Admin Inicial (Apenas no Primeiro Deploy: não pode ficar vazio)
ADMIN_NAME=Admin Principal
ADMIN_EMAIL=admin@ufpb.br
ADMIN_PASSWORD=senha-super-segura
```

### Passo 3: Adicionar os Mounts / Volumes de Dados
A aplicação baixa fotos de perfis do web, grava áudios trocados e gerencia históricos provisórios na própria máquina enquanto consolida conversas. Na aba **Storage / Volumes** (ou equivalente) no Easypanel, crie **dois volumes persistentes** cruciais para que as mídias anexadas não se percam cada vez que a instância reiniciar:
1. `Local Path`: `/app/uploads` | `Volume Name`: `uploads_data`
2. `Local Path`: `/app/runtime` | `Volume Name`: `runtime_data`

Pronto. Só clicar em **Deploy** no Easypanel! O script de bootstrap iniciará executável de Saúde `startup_check.py` e cuidará de aplicar todas as tabelas em seu banco de dados PostgreSQL do zero automaticamente.

---

## 🛠️ Outras Formas de Instalação (Local)

### Com Docker Compose
1. Faça o clone do repositório.
2. Copie os envs: `cp .env.example .env` e substitua para seu contexto.
3. Suba as instâncias atreladas: 
```bash
docker compose -f docker-compose.production.yml up -d --build
```
4. Acesso Front-End: `http://localhost:8000/inbox`
5. Acesso Swagger da API Completa: `http://localhost:8000/api/v1/docs`

---

## 🔧 Exceções e Regras Vitais do Negócio

### Número Oficial de Atendimento (Evasão de Duplicidade)

Para evitar loops de mensagens e a duplicação severa de conversas — onde o sistema tentaria criar um chat recursivo com o próprio número do bot no inbox —, o telefone principal do atendimento está bloqueado "hardcoded".

Atualmente, o sistema possui a regra restritiva de ignorar a criação de instâncias de conversas associadas ao número **+558332167336**.

> **⚠️ IMPORTANTE:** Se futuramente o número oficial de atendimento da UFPB for alterado, você deverá modificar essa restrição para que o comportamento opere corretamente com a nova linha.  
> Abra o arquivo de ingestão genérica de mensagens (`app/services/messages.py`), procure pela função `ingest_inbound_message` e altere a seguinte condicional refetindo o novo número:

```python
    # Ignore webhooks where the contact phone is the UFPB system bot itself
    if contact_phone == "+55NOVO_NUMERO_AQUI":
        return None
```
Nenhuma tela nativamente visual da UI permite alterar essa tolerância, pois trata-se de um bloqueio estrutural do webhook raiz (medida passiva de segurança). Se for alterar o número geral da instituição, o código-fonte ali deverá ser revisado.

---

## 🔐 Segurança da Arquitetura

O sistema emprega diretrizes rígidas sobre persistência e validação:
- **Challenge-Response Login**: Cria "charadas" temporárias impedindo automações por bots simples em rotas estáticas e foros abertos.
- **Segurança de Sessão Sem Estado**: Tokens JWT fluindo exclusivamente via Authorization Header; imunes nativamente a CSRF.
- **Factory Pattern e Clean Code**: Empregados integralmente no diretório `app/core/app_factory.py`. Ele injeta Middlewares de Logging global, gerencia o ciclo `lifespan` com maestria aguardando sempre que o database inicialize a conexão limpa antes de despachar rotas HTTP.

## 🤝 Contribuição e Manutenção
- Este projeto incorpora paradigmas estritos baseados na arquitetura **Loosely Coupled**, de modo que as Interfaces (`app/static/...`) e as camadas de Serviços (`app/services/...`) existam abstraídas.  
- Durante ajustes na interface original presente em `/inbox`, leve sempre em conta não desvincular do seletor IDs da DOM mapeados de forma estática no objeto `els` da raiz principal de controle (`app/static/inbox/app.js`).
- Mantido ativamente na versão `2.0.0` pela **Equipe UFPB Chat**.
