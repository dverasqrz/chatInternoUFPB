# UFPB Chat System

Sistema de chat institucional da UFPB com integração WhatsApp, gerenciamento de usuários e recursos avançados.

## Features

- **Chat em tempo real** com interface moderna
- **Integração WhatsApp** via webhooks
- **Gerenciamento de usuários** com controle de acesso
- **Upload de mídia** (imagens, áudios)
- **Sistema administrativo** completo
- **Limpeza de dados** com segurança
- **Interface responsiva** e intuitiva
- **Sistema de Templates** com controle administrativo
- **Templates LGPD** para conformidade automática
- **Modo offline** com fallback inteligente

## 📁 Estrutura do Projeto

```
chatZapUFPB/
├── app/                    # Aplicação principal
│   ├── api/               # Endpoints da API
│   │   ├── routes/        # Rotas da API
│   │   └── dependencies.py # Dependências FastAPI
│   ├── core/              # Configuração principal
│   │   ├── app_factory.py # Fábrica da aplicação
│   │   ├── config.py      # Configurações
│   │   └── security.py    # Segurança
│   ├── db/                # Banco de dados
│   │   ├── base.py        # Modelo base
│   │   └── session.py     # Sessão DB
│   ├── models/            # Models SQLAlchemy
│   │   ├── user.py        # Modelo de usuário
│   │   ├── message.py     # Modelo de mensagem
│   │   ├── conversation.py # Modelo de conversa
│   │   └── runtime_settings.py # Configurações runtime
│   ├── schemas/           # Schemas Pydantic
│   │   ├── user.py        # Schemas de usuário
│   │   ├── message.py     # Schemas de mensagem
│   │   └── admin.py       # Schemas admin
│   ├── services/          # Lógica de negócio
│   │   ├── auth.py        # Autenticação
│   │   ├── media.py       # Processamento de mídia
│   │   └── runtime_settings.py # Config. runtime
│   ├── static/            # Arquivos estáticos
│   │   └── inbox/         # Interface web
│   │       ├── index.html # Página principal
│   │       ├── app.js     # Lógica frontend
│   │       └── styles.css # Estilos
│   └── utils/             # Utilitários
│       ├── logging.py     # Configuração de logs
│       └── validators.py  # Validadores
├── uploads/               # Arquivos upload
├── runtime/               # Arquivos runtime
├── logs/                  # Logs da aplicação
├── scripts/               # Scripts auxiliares
├── .env                   # Variáveis ambiente
├── .env.example          # Exemplo de .env
├── docker-compose.yml     # Docker Compose
├── Dockerfile            # Docker image
└── requirements.txt       # Dependências Python
```

## 🛠️ Instalação

### Pré-requisitos
- Docker e Docker Compose
- Python 3.11+ (para desenvolvimento local)

### Com Docker (Recomendado)

1. **Clone o repositório**
```bash
git clone <repository-url>
cd chatZapUFPB
```

2. **Configure as variáveis ambiente**
```bash
cp .env.example .env
# Edite .env com suas configurações
```

3. **Inicie os serviços**
```bash
docker compose up -d --build
```

4. **Acesse a aplicação**
- Frontend: http://localhost:8000/inbox/
- API: http://localhost:8000/api/v1/docs

### Desenvolvimento Local

1. **Instale dependências**
```bash
pip install -r requirements.txt
```

2. **Configure o banco de dados**
```bash
# Configure PostgreSQL no .env
# Execute as migrações se necessário
```

3. **Inicie a aplicação**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 Configuração

### Variáveis Ambiente (.env)

```env
# Banco de Dados
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/dbname

# Segurança
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Administrador
ADMIN_NAME=Nome Admin
ADMIN_EMAIL=admin@ufpb.br
ADMIN_PASSWORD=secure_password

# WhatsApp
N8N_WEBHOOK_URL=http://localhost:5678/webhook/whatsapp
WEBHOOK_TOKEN=your-webhook-token

# CORS
CORS_ORIGINS=http://localhost:8000,http://localhost:3000
```

### Número Oficial de Atendimento (Evasão de Duplicidade)

Para evitar loops de mensagens e a duplicação de conversas — onde o sistema tentaria criar um chat com o próprio número do bot no inbox —, o telefone principal do atendimento está bloqueado via código ("hardcoded") no arquivo de ingestão de webhooks.

Atualmente, o sistema possui a regra de ignorar a criação de novas instâncias de conversas associadas ao número **+558332167336**.

> **⚠️ IMPORTANTE:** Se futuramente o número oficial de atendimento da UFPB for alterado, você deverá modificar essa restrição para que o comportamento opere corretamente com a nova linha.  
> Abra o arquivo genérico de mensagens (`app/services/messages.py`), procure pela função `ingest_inbound_message` (por volta da linha 445) e altere a seguinte condicional para refletir o novo número:

```python
    # Ignore webhooks where the contact phone is the UFPB system bot itself
    if contact_phone == "+55NOVO_NUMERO_AQUI":
        return None
```

Atualizando esse arquivo e reiniciando a aplicação, o sistema passará automaticamente a ignorar logs duplicados envolvendo esse novo número.

## 📚 Documentação da API

Acesse a documentação interativa em:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 🔐 Autenticação

O sistema usa JWT para autenticação:

1. **Challenge-Response**: Sistema de charadas para login
2. **Token JWT**: Sessão segura com expiração
3. **Roles**: Usuário comum vs Administrador

## 🎯 Principais Endpoints

### Autenticação
- `GET /api/v1/auth/challenge` - Obter charada
- `POST /api/v1/auth/login` - Fazer login
- `POST /api/v1/auth/logout` - Fazer logout

### Usuários (Admin)
- `GET /api/v1/users` - Listar usuários
- `POST /api/v1/users` - Criar usuário
- `PATCH /api/v1/users/{id}/status` - Ativar/Desativar
- `DELETE /api/v1/users/{id}` - Excluir usuário

### Conversas
- `GET /api/v1/conversations` - Listar conversas
- `GET /api/v1/conversations/{id}/messages` - Mensagens
- `POST /api/v1/conversations/{id}/export` - Exportar

### Upload de Mídia
- `POST /api/v1/uploads/media` - Upload de arquivos
- `GET /uploads/{filename}` - Acessar arquivos

### Administração
- `DELETE /api/v1/admin/cleanup/messages` - Limpar mensagens
- `DELETE /api/v1/admin/cleanup/uploads` - Limpar uploads

### Templates
- `GET /api/v1/templates/` - Listar templates
- `POST /api/v1/templates/` - Criar template (admin)
- `PUT /api/v1/templates/{id}/` - Atualizar template (admin)
- `DELETE /api/v1/templates/{id}/` - Excluir template (admin)
- `POST /api/v1/templates/initialize` - Inicializar templates do sistema (admin)

## Templates de Mensagens

### Sistema de Templates
O sistema inclui um gerenciador completo de templates de mensagens:

#### Templates do Sistema (Protegidos)
- **LGPD**: Termo de consentimento para tratamento de dados
- **Pesquisa**: Formulário de satisfação pós-atendimento

#### Funcionalidades
- **Acesso rápido**: Digite `/` no campo de mensagem
- **Administração**: Apenas admins podem criar/editar/excluir
- **Modo offline**: Fallback automático se backend estiver offline
- **Categorias**: Organização por categorias (LGPD, Pesquisa, etc.)

#### Como Usar
1. **Para Atendentes**: Digite `/` e selecione o template desejado
2. **Para Admins**: Acesse área administrativa > "Gerenciamento de Templates"
3. **Criar Novo**: Como admin, clique em "Novo Template"
4. **Editar/Excluir**: Use os botões de ação na lista de templates

## Deploy em Produção

### EasyPanel
Para implantar no EasyPanel ou similar:

1. **Preparar Ambiente**
```bash
git clone <repository-url>
cd chatZapUFPB
cp .env.example .env
# Configure .env com credenciais reais
```

2. **Configurar Variáveis Essenciais**
```env
SECRET_KEY=chave-longa-e-aleatoria
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname
PUBLIC_DOMAIN=https://seu-dominio.com
CORS_ORIGINS=https://seu-dominio.com
ENVIRONMENT=production
DEBUG=false
```

3. **Deploy Automático**
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

4. **Deploy Manual**
```bash
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d
```

### Configurações de Produção

#### Segurança
- Use `SECRET_KEY` forte e aleatória
- Configure `CORS_ORIGINS` com domínio real
- Use HTTPS em produção
- Configure backup automático

#### Banco de Dados
- PostgreSQL recomendado
- Configure backups diários
- Monitore performance
- Use connection pooling

#### Monitoramento
- Logs: `docker-compose logs -f app`
- Health checks: `/health`
- Métricas: Configure monitoring
- Alertas: Configure notificações

### Scripts Úteis

#### Deploy Automático
```bash
# Script completo de deploy
./scripts/deploy.sh
```

#### Inicialização de Templates
```bash
# Se necessário, execute manualmente
python scripts/init_templates.py
```

#### Backup do Banco
```bash
# Backup completo
docker exec ufpb_db_prod pg_dump -u ufpb ufpb_chat > backup_$(date +%Y%m%d).sql
```

## Interface Web

### Features
- **Chat em tempo real** com polling inteligente
- **Upload arrastar-e-soltar**
- **Gravação de áudio** com visualizador
- **Interface responsiva**
- **Notificações toast**
- **Scroll infinito**

### Acessibilidade
- Navegação por teclado
- Contraste adequado
- Feedback visual claro
- Mensagens de erro informativas

## 🔒 Segurança

### Implementações
- **JWT tokens** com expiração
- **Password hashing** bcrypt
- **CORS configurado**
- **SQL injection protection** via ORM
- **XSS protection** no frontend
- **Rate limiting** (recomendado)

### Boas Práticas
- Validação de entrada
- Sanitização de dados
- Logs de auditoria
- Backup automático
- Monitoramento

## 📊 Monitoramento

### Logs
- **Aplicação**: `/app/logs/`
- **Nível**: INFO, WARNING, ERROR
- **Rotação**: Configurável
- **Formato**: Estruturado

### Health Checks
- **API**: `/health`
- **Database**: Verificação de conexão
- **FFmpeg**: Verificação de dependências

## 🚀 Deploy

### Produção
1. Configure variáveis ambiente
2. Use HTTPS
3. Configure backup
4. Monitore logs
5. Atualize regularmente

### Docker
```bash
# Build produção
docker build -t ufpb-chat .

# Run produção
docker run -d --name ufpb-chat -p 8000:8000 ufpb-chat
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie branch feature
3. Commit mudanças
4. Push para branch
5. Abra Pull Request

### Padrões
- **Python**: PEP 8
- **JavaScript**: ES6+
- **CSS**: BEM methodology
- **Commits**: Conventional Commits

## 📝 Licença

Este projeto é propriedade da UFPB.

## 🆘 Suporte

Para suporte técnico:
- Equipe de TI da UFPB
- Documentação interna
- Sistema de tickets

---

**Versão**: 2.0.0  
**Última atualização**: 2026-04-06  
**Maintainer**: Equipe UFPB Chat
