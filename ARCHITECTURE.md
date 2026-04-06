# Arquitetura do Sistema UFPB Chat

## 🏗️ Visão Geral

Sistema de chat institucional construído com FastAPI (backend) e JavaScript vanilla (frontend), seguindo princípios de baixo acoplamento e alta coesão.

## 📐 Arquitetura

### Backend (FastAPI)
- **Framework**: FastAPI com Python 3.11+
- **ORM**: SQLAlchemy com PostgreSQL
- **Validação**: Pydantic schemas
- **Autenticação**: JWT com challenge-response
- **Documentação**: OpenAPI/Swagger automática

### Frontend
- **Framework**: JavaScript vanilla (sem frameworks)
- **Arquitetura**: Módulos ES6, orientada a objetos
- **Estilos**: CSS3 com variáveis CSS
- **Build**: Sem build step, código direto

### Infraestrutura
- **Containerização**: Docker + Docker Compose
- **Banco**: PostgreSQL 16
- **Reverse Proxy**: Uvicorn (interno)
- **Storage**: Volume Docker para uploads

## 🔄 Fluxo de Dados

```
Frontend (Browser)
    ↓ HTTP/WebSocket
FastAPI (API Gateway)
    ↓ Injeção de Dependências
Services (Business Logic)
    ↓ SQLAlchemy ORM
PostgreSQL (Database)
    ↓ Volume Docker
File System (Uploads)
```

## 📦 Módulos Principais

### 1. Core (`app/core/`)
**Responsabilidade**: Configuração central e inicialização

```python
app_factory.py  # Fábrica da aplicação
config.py       # Configurações de ambiente
security.py     # Lógica de segurança
```

**Princípios**:
- Single Responsibility: Cada arquivo tem uma função clara
- Dependency Injection: Configuração injetada onde necessária
- Environment-based: Configurações separadas por ambiente

### 2. API (`app/api/`)
**Responsabilidade**: Endpoints HTTP e validação

```python
routes/
├── auth.py        # Autenticação
├── users.py       # Gerenciamento de usuários
├── conversations.py # Conversas e mensagens
├── uploads.py     # Upload de mídia
└── admin.py       # Funções administrativas
```

**Princípios**:
- RESTful: URLs seguindo padrões REST
- Validation: Pydantic schemas para validação
- Error Handling: Respostas consistentes
- Documentation: OpenAPI automática

### 3. Services (`app/services/`)
**Responsabilidade**: Lógica de negócio

```python
auth.py              # Autenticação e autorização
media.py             # Processamento de mídia
runtime_settings.py # Configurações dinâmicas
```

**Princípios**:
- Business Logic: Separada da camada de API
- Testability: Fácil de testar unitariamente
- Reusability: Lógica compartilhada entre endpoints

### 4. Models (`app/models/`)
**Responsabilidade**: Modelo de dados

```python
user.py           # Modelo de usuário
message.py        # Modelo de mensagem
conversation.py  # Modelo de conversa
runtime_settings.py # Configurações runtime
```

**Princípios**:
- ORM: SQLAlchemy com relacionamentos claros
- Validation: Constraints a nível de modelo
- Migrations: Versionamento do schema

### 5. Schemas (`app/schemas/`)
**Responsabilidade**: Serialização/Validação

```python
user.py      # Schemas de usuário
message.py   # Schemas de mensagem
admin.py     # Schemas administrativos
```

**Princípios**:
- Separation: Separação de models e API schemas
- Validation: Validação robusta com Pydantic
- Documentation: Geração automática de docs

## 🔌 Padrões e Princípios

### 1. Dependency Injection
```python
# Injeção de dependências FastAPI
def get_db() -> Generator[Session, None, None]:
    """Sessão do banco de dados"""
    
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Usuário autenticado"""
```

### 2. Repository Pattern (Implícito)
```python
# Services encapsulam acesso a dados
class AuthService:
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()
```

### 3. Service Layer Pattern
```python
# Lógica de negócio separada
class MediaService:
    def upload_media(self, file: UploadFile) -> MediaUploadResponse:
        # Validação, processamento, armazenamento
```

### 4. DTO Pattern (Schemas Pydantic)
```python
# Transferência de dados entre camadas
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
```

## 🎯 Baixo Acoplamento

### 1. Frontend-Backend
- **Interface**: API REST bem definida
- **Independência**: Frontend pode ser substituído
- **Comunicação**: JSON via HTTP

### 2. Database-Application
- **ORM**: SQLAlchemy abstrai o banco
- **Migrations**: Controle de versão do schema
- **Pool**: Conexões gerenciadas

### 3. Services-API
- **Injeção**: Services injetados nos endpoints
- **Interfaces**: Contratos claros entre camadas
- **Testabilidade**: Isolamento para testes

## 🔧 Configuração

### Environment-based Configuration
```python
# config.py
class Settings(BaseSettings):
    database_url: str
    secret_key: str
    environment: str = "development"
    
    class Config:
        env_file = ".env"
```

### Feature Flags
```python
# Habilitação de features por ambiente
ENABLE_VIDEO_PROCESSING = settings.environment == "production"
ENABLE_ADMIN_FEATURES = settings.environment != "testing"
```

## 🚀 Performance

### 1. Database
- **Indexing**: Índices em colunas frequentemente consultadas
- **Connection Pool**: Pool de conexões eficiente
- **Query Optimization**: Queries otimizadas com ORM

### 2. Frontend
- **Lazy Loading**: Carregamento sob demanda
- **Polling Inteligente**: Pausa durante mídia
- **Cache**: Cache de recursos estáticos

### 3. File Storage
- **Volume Docker**: Performance de I/O otimizada
- **FFmpeg**: Processamento assíncrono
- **Cleanup**: Limpeza automática de arquivos

## 🔒 Segurança

### 1. Autenticação
```python
# JWT com expiração
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
```

### 2. Autorização
```python
# Decoradores de permissão
def get_current_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
```

### 3. Validação
```python
# Validação robusta
class UserCreate(BaseModel):
    password: str = Field(..., min_length=8, regex=r"^(?=.*[A-Za-z])(?=.*\d)")
```

## 📊 Monitoramento

### 1. Logs Estruturados
```python
# Logging configurado
logger = logging.getLogger(__name__)
logger.info("User authenticated", extra={"user_id": user.id, "email": user.email})
```

### 2. Health Checks
```python
# Verificação de saúde
@router.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

### 3. Metrics
- **Response Time**: Tempo de resposta
- **Error Rate**: Taxa de erros
- **Active Users**: Usuários ativos

## 🧪 Testabilidade

### 1. Unit Tests
```python
# Services testáveis
def test_auth_service():
    service = AuthService()
    result = service.authenticate_user("test@example.com", "password")
    assert result is not None
```

### 2. Integration Tests
```python
# API endpoints testáveis
def test_login_endpoint(client):
    response = client.post("/api/v1/auth/login", json={...})
    assert response.status_code == 200
```

### 3. E2E Tests
- **Frontend**: Testes de interface
- **Workflows**: Testes de fluxo completo
- **Performance**: Testes de carga

## 🔄 Evolução

### 1. Escalabilidade
- **Horizontal**: Múltiplas instâncias
- **Vertical**: Mais recursos por instância
- **Database**: Read replicas, sharding

### 2. Features Futuras
- **WebSocket**: Comunicação em tempo real
- **File Storage**: S3/MinIO integration
- **Analytics**: Dashboards e métricas
- **Mobile**: App nativo

### 3. Manutenibilidade
- **Documentation**: Docs sempre atualizadas
- **Code Quality**: Linting e formatação
- **Dependencies**: Dependências atualizadas
- **Security**: Patches de segurança

---

**Esta arquitetura foi desenhada para ser escalável, mantível e segura, seguindo as melhores práticas de desenvolvimento de software moderno.**
