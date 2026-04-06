# Guia de Desenvolvimento UFPB Chat System

## 🚀 Setup do Ambiente de Desenvolvimento

### Pré-requisitos
- Python 3.11+
- Docker e Docker Compose
- PostgreSQL (se não usar Docker)
- Git
- VS Code (recomendado)

### 1. Clone e Setup
```bash
git clone <repository-url>
cd chatZapUFPB
cp .env.example .env
# Configure .env com suas credenciais
```

### 2. Ambiente Docker (Recomendado)
```bash
# Inicie todos os serviços
docker compose up -d --build

# Verifique logs
docker compose logs -f app

# Pare os serviços
docker compose down
```

### 3. Ambiente Local
```bash
# Instale dependências
pip install -r requirements.txt

# Configure banco de dados PostgreSQL
# Edite .env com DATABASE_URL correto

# Inicie a aplicação
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📁 Estrutura de Código

### Backend (FastAPI)
```
app/
├── core/              # Configuração central
│   ├── app_factory.py # Fábrica da aplicação
│   ├── config.py      # Configurações
│   ├── security.py    # Segurança
│   └── logging.py     # Logs
├── api/               # Endpoints e rotas
│   ├── routes/        # Definição de rotas
│   └── dependencies.py # Injeção de dependências
├── models/            # Models SQLAlchemy
├── schemas/           # Schemas Pydantic
├── services/          # Lógica de negócio
├── db/                # Configuração DB
└── utils/             # Utilitários
```

### Frontend (JavaScript Vanilla)
```
app/static/inbox/
├── index.html         # Estrutura HTML
├── app.js            # Lógica JavaScript
└── styles.css        # Estilos CSS
```

## 🔧 Padrões de Código

### Python (PEP 8)
```python
# Imports no topo
import logging
from typing import Optional

from fastapi import FastAPI
from sqlalchemy.orm import Session

# Constantes em MAIÚSCULAS
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30

# Classes PascalCase
class UserService:
    """Service for user management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with validation."""
        # Implementation
        pass

# Funções snake_case
def get_current_user(token: str) -> Optional[User]:
    """Get current user from JWT token."""
    # Implementation
    pass

# Variáveis snake_case
user_id = 123
is_active = True
```

### JavaScript (ES6+)
```javascript
// Constants em UPPER_CASE
const API_PREFIX = "/api/v1";
const MAX_RETRY_ATTEMPTS = 3;

// Classes PascalCase
class UserService {
    constructor(apiClient) {
        this.apiClient = apiClient;
    }
    
    async createUser(userData) {
        try {
            const response = await this.apiClient.post('/users', userData);
            return response.data;
        } catch (error) {
            console.error('Failed to create user:', error);
            throw error;
        }
    }
}

// Functions camelCase
function getCurrentUser() {
    return state.user;
}

// Variables camelCase
let userId = 123;
let isActive = true;
```

### CSS (BEM Methodology)
```css
/* Block */
.chat-container {
    display: flex;
    flex-direction: column;
}

/* Element */
.chat-container__header {
    padding: 16px;
    border-bottom: 1px solid #eee;
}

/* Modifier */
.chat-container--compact {
    max-height: 400px;
}

.chat-container__header--minimal {
    padding: 8px;
}
```

## 🧪 Testes

### Testes Unitários
```bash
# Execute todos os testes
pytest

# Execute com coverage
pytest --cov=app

# Execute teste específico
pytest tests/test_user_service.py
```

### Testes de API
```bash
# Testes de endpoints
pytest tests/test_api/

# Testes de integração
pytest tests/test_integration/
```

### Testes Frontend
```bash
# Testes JavaScript (se implementados)
npm test

# Testes E2E (se implementados)
npm run test:e2e
```

## 🔍 Debugging

### Backend Debug
```python
# Use logging estruturado
logger.info("User login attempt", extra={
    "user_id": user.id,
    "email": user.email,
    "timestamp": datetime.utcnow()
})

# Use debugger
import pdb; pdb.set_trace()

# FastAPI debug mode
uvicorn app.main:app --reload --debug
```

### Frontend Debug
```javascript
// Use console logging estruturado
console.log('User login attempt', {
    userId: user.id,
    email: user.email,
    timestamp: new Date()
});

// Use debugger
debugger;

// Network debugging
fetch('/api/v1/users')
    .then(response => console.log('Response:', response))
    .catch(error => console.error('Error:', error));
```

### Docker Debug
```bash
# Logs em tempo real
docker compose logs -f app

# Entrar no container
docker exec -it ufpb_app bash

# Verificar ambiente
docker exec ufpb_app env | sort
```

## 📝 Logging

### Backend Logging
```python
import logging

logger = logging.getLogger(__name__)

# Logs estruturados
logger.info("User created successfully", extra={
    "user_id": user.id,
    "email": user.email,
    "action": "user_created"
})

# Logs de erro
logger.error("Failed to create user", extra={
    "error": str(error),
    "email": user_data.email,
    "action": "user_creation_failed"
}, exc_info=True)
```

### Frontend Logging
```javascript
// Logging estruturado
const log = {
    info: (message, data = {}) => {
        console.log(`[INFO] ${message}`, data);
    },
    error: (message, error = null) => {
        console.error(`[ERROR] ${message}`, error);
    },
    debug: (message, data = {}) => {
        if (process.env.NODE_ENV === 'development') {
            console.debug(`[DEBUG] ${message}`, data);
        }
    }
};
```

## 🔄 Fluxo de Trabalho

### 1. Feature Development
```bash
# 1. Crie branch
git checkout -b feature/nova-funcionalidade

# 2. Desenvolva
# - Escreva código
# - Escreva testes
# - Atualize docs

# 3. Teste
pytest
npm test  # se aplicável

# 4. Commit
git add .
git commit -m "feat: add nova funcionalidade"

# 5. Push e PR
git push origin feature/nova-funcionalidade
```

### 2. Bug Fix
```bash
# 1. Branch de bug
git checkout -b fix/descricao-do-bug

# 2. Reproduza e corrija
# - Adicione teste que reproduz o bug
# - Corrija o código
# - Verifique que o teste passa

# 3. Commit
git commit -m "fix: resolve descricao-do-bug"

# 4. Push e PR
git push origin fix/descricao-do-bug
```

### 3. Code Review Checklist
- [ ] Código segue padrões do projeto
- [ ] Testes passam
- [ ] Documentação atualizada
- [ ] Logs apropriados
- [ ] Sem segredos expostos
- [ ] Performance considerada
- [ ] Segurança revisada

## 🚀 Deploy

### Deploy em Produção
```bash
# 1. Build da imagem
docker build -t ufpb-chat:latest .

# 2. Tag para produção
docker tag ufpb-chat:latest registry.example.com/ufpb-chat:v2.0.0

# 3. Push
docker push registry.example.com/ufpb-chat:v2.0.0

# 4. Deploy (kubectl ou similar)
kubectl apply -f k8s/production.yaml
```

### Environment Variables
```bash
# Produção
export DATABASE_URL="postgresql://..."
export SECRET_KEY="production-secret"
export ENVIRONMENT="production"

# Desenvolvimento
export DATABASE_URL="postgresql://localhost/ufpb_dev"
export SECRET_KEY="dev-secret"
export ENVIRONMENT="development"
```

## 📊 Performance

### Backend Performance
```python
# Use database indexes
class User(Base):
    email = Column(String, index=True)  # Index para busca
    created_at = Column(DateTime, index=True)  # Index para ordenação

# Use connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)

# Cache queries frequentes
from functools import lru_cache

@lru_cache(maxsize=128)
def get_user_settings(user_id: int):
    # Cache de configurações de usuário
    pass
```

### Frontend Performance
```javascript
// Lazy loading de componentes
const loadComponent = async (componentName) => {
    const module = await import(`./components/${componentName}.js`);
    return module.default;
};

// Debounce para eventos pesados
const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// Virtual scroll para listas grandes
class VirtualScroll {
    constructor(container, itemHeight, renderItem) {
        this.container = container;
        this.itemHeight = itemHeight;
        this.renderItem = renderItem;
    }
    
    render(items) {
        // Implementação de virtual scroll
    }
}
```

## 🔒 Segurança

### Backend Security
```python
# Validação de entrada
from pydantic import validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

# Sanitização de dados
import bleach

def sanitize_html(html: str) -> str:
    return bleach.clean(html, tags=['b', 'i', 'u'])

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/login")
@limiter.limit("5/minute")
async def login():
    # Implementation
    pass
```

### Frontend Security
```javascript
// XSS prevention
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// CSRF protection
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

fetch('/api/v1/data', {
    method: 'POST',
    headers: {
        'X-CSRF-Token': csrfToken,
        'Content-Type': 'application/json'
    }
});
```

## 📚 Recursos Adicionais

### Documentação
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [JavaScript MDN](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript)

### Ferramentas
- **API Testing**: Postman, Insomnia
- **Database**: pgAdmin, DBeaver
- **Code Quality**: Black, Flake8, ESLint
- **Performance**: Locust, JMeter

### Monitoramento
- **Logs**: ELK Stack, Grafana
- **Metrics**: Prometheus, Grafana
- **APM**: Sentry, New Relic

---

**Este guia serve como referência para desenvolvimento do UFPB Chat System. Mantenha-o atualizado com as melhores práticas e padrões do projeto.**
