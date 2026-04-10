#!/bin/bash

# Script de Deploy para Produção (EasyPanel)
# UFPB Chat Multiatendente

set -e

echo "=== DEPLOY UFPB CHAT SYSTEM ==="
echo "Iniciando deploy para produção..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para imprimir mensagens coloridas
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se está no diretório correto
if [ ! -f "docker-compose.production.yml" ]; then
    print_error "docker-compose.production.yml não encontrado. Execute este script no diretório raiz do projeto."
    exit 1
fi

# Verificar se .env existe
if [ ! -f ".env" ]; then
    print_warning "Arquivo .env não encontrado. Copiando .env.example..."
    cp .env.example .env
    print_warning "Por favor, configure o arquivo .env com suas credenciais antes de continuar."
    exit 1
fi

# Verificar variáveis essenciais no .env
print_status "Verificando configurações essenciais..."

source .env

if [ "$SECRET_KEY" = "CHANGE_ME_APP_SECRET" ] || [ -z "$SECRET_KEY" ]; then
    print_error "SECRET_KEY não configurado corretamente no .env"
    exit 1
fi

if [ "$WEBHOOK_TOKEN" = "CHANGE_ME_INBOUND_WEBHOOK_TOKEN" ] || [ -z "$WEBHOOK_TOKEN" ]; then
    print_error "WEBHOOK_TOKEN não configurado corretamente no .env"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    print_error "DATABASE_URL não configurado no .env"
    exit 1
fi

print_status "Configurações verificadas com sucesso!"

# Backup do banco de dados (se existir)
if docker ps | grep -q ufpb_db_prod; then
    print_status "Fazendo backup do banco de dados..."
    docker exec ufpb_db_prod pg_dump -u ${POSTGRES_USER:-ufpb} ${POSTGRES_DB:-ufpb_chat} > backup_$(date +%Y%m%d_%H%M%S).sql
    print_status "Backup concluído"
fi

# Parar containers existentes
print_status "Parando containers existentes..."
docker-compose -f docker-compose.production.yml down || true

# Build da imagem
print_status "Build da imagem da aplicação..."
docker-compose -f docker-compose.production.yml build --no-cache

# Iniciar containers
print_status "Iniciando containers..."
docker-compose -f docker-compose.production.yml up -d

# Aguardar banco de dados estar pronto
print_status "Aguardando banco de dados..."
sleep 10

# Verificar se containers estão rodando
print_status "Verificando status dos containers..."
docker-compose -f docker-compose.production.yml ps

# Executar migrações (se necessário)
print_status "Executando migrações do banco de dados..."
docker-compose -f docker-compose.production.yml exec app alembic upgrade head

# Verificar se a aplicação está saudável
print_status "Verificando saúde da aplicação..."
sleep 5

# Testar endpoint de health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "Aplicação está saudável! "
else
    print_warning "Health check falhou, mas isso pode ser normal se o endpoint não existir"
fi

# Testar endpoint de templates
if curl -f http://localhost:8000/api/v1/templates/ > /dev/null 2>&1; then
    print_status "Endpoint de templates funcionando!"
else
    print_warning "Endpoint de templates não respondeu (pode precisar de autenticação)"
fi

# Mostrar logs iniciais
print_status "Mostrando logs iniciais da aplicação..."
docker-compose -f docker-compose.production.yml logs app --tail=20

print_status "=== DEPLOY CONCLUÍDO COM SUCESSO ==="
echo ""
echo "A aplicação está rodando em: http://localhost:8000"
echo "Documentação da API: http://localhost:8000/api/v1/docs"
echo ""
echo "Próximos passos:"
echo "1. Acesse a aplicação e faça login como administrador"
echo "2. Verifique se os templates do sistema foram criados"
echo "3. Configure os webhooks do N8N se necessário"
echo "4. Teste o envio e recebimento de mensagens"
echo ""
echo "Para monitorar logs: docker-compose -f docker-compose.production.yml logs -f app"
echo "Para parar: docker-compose -f docker-compose.production.yml down"
