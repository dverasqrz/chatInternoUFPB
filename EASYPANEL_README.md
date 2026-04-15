# EasyPanel Deployment Guide

## Problema Identificado
O projeto estava falhando no EasyPanel porque:
1. O script de startup fazia verificações rigorosas de FFmpeg que podiam falhar
2. O docker-compose.yml tinha dependências complexas e volumes locais
3. O healthcheck dependia de testes funcionais que podiam não funcionar em todos os ambientes

## Soluções Aplicadas

### 1. Script de Startup Simplificado
- Removido teste funcional rigoroso do FFmpeg
- FFmpeg agora é opcional (sistema funciona sem ele)
- Verificações de diretório mantidas

### 2. Docker Compose Otimizado
- Criado `docker-compose.easypanel.yml` com configurações simplificadas
- Healthcheck do app usa curl para `/health` em vez de FFmpeg
- Volumes nomeados em vez de locais
- Todas as variáveis de ambiente explicitamente definidas

### 3. Dockerfile Simplificado
- Criado `Dockerfile.easypanel` sem script de startup complexo
- Healthcheck direto via curl
- Comando de startup direto com uvicorn

## Como Usar no EasyPanel

### Opção 1: Usar Imagem Pré-construída (Recomendado)
1. No EasyPanel, crie um novo projeto
2. Use a imagem: `dverazs/chatzapufpb:v1`
3. Configure as variáveis de ambiente necessárias
4. Configure um banco PostgreSQL separado
5. Use volumes para uploads, runtime e logs

### Opção 2: Build Customizado
1. Use o `Dockerfile.easypanel` e `docker-compose.easypanel.yml`
2. Faça build da imagem no EasyPanel
3. Configure as variáveis de ambiente

## Variáveis de Ambiente Essenciais

```bash
# Database
DATABASE_URL=postgresql://user:password@db_host:5432/db_name

# Security
SECRET_KEY=your-secret-key-here
WEBHOOK_TOKEN=your-webhook-token

# Admin
ADMIN_EMAIL=admin@domain.com
ADMIN_NAME=Admin Name

# Domain
PUBLIC_DOMAIN=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
```

## Health Checks
- O app agora usa `/health` como healthcheck
- Certifique-se de que o banco está acessível antes de iniciar o app
- O FFmpeg é opcional - o sistema funciona sem ele

## Troubleshooting
- Se ainda falhar, verifique os logs do container
- Certifique-se de que todas as variáveis de ambiente estão definidas
- O banco PostgreSQL deve estar saudável antes do app iniciar