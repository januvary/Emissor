# Olostech Automation

Sistema de automação para registro de dispensações no Olostech W6 usando análise HAR e desenvolvimento offline.

## 🚀 Quick Start

### Desenvolvimento Offline (Recomendado)

```bash
# 1. Inicie mock server
./scripts/start_mock_server.sh

# 2. Execute testes
pytest tests/integration/ -v

# 3. Desenvolva!
```

### Teste com Olostech Real

```bash
# Configure credenciais
cp config/.env.example config/.env
nano config/.env

# Execute workflow
pytest tests/e2e/test_login_workflow.py -v
```

## ✨ Funcionalidades

- ✅ **Desenvolvimento Offline** - Mock server permite iterar sem Olostech
- ✅ **Dashboard Gráfico** - Interface CustomTkinter para registro manual
- ✅ **Cliente API** - Interação via HTTP (10-20x mais rápido que Selenium)
- ✅ **HAR Tools** - Extração e análise de tráfego HTTP
- ✅ **Testes Completos** - 140+ testes organizados por tipo

## 📚 Documentação

- **[Primeiros Passos](docs/00_START_HERE.md)** - Por onde começar
- **[Arquitetura](docs/01_architecture.md)** - Visão geral do sistema
- **[Mock Server](docs/03_mock_server.md)** - Desenvolvimento offline
- **[API Reference](docs/04_api_reference.md)** - Documentação completa da API
- **[Contribuindo](CONTRIBUTING.md)** - Guia de contribuição

## 🧪 Testes

| Tipo | Local | Comando |
|------|-------|---------|
| Unitários | `tests/unit/` | `pytest tests/unit/ -v` |
| Integração | `tests/integration/` | `pytest tests/integration/ -v` |
| E2E | `tests/e2e/` | `pytest tests/e2e/ -v` |
| Todos | `tests/` | `./scripts/run_all_tests.sh` |

**Resultados Atuais:**
- ✅ 87+ testes unitários
- ✅ 28+ testes de integração
- ✅ 25+ testes de regressão
- ✅ 3+ testes E2E

## 📁 Estrutura

```
olostech_automation/
├── docs/              # Documentação completa
│   ├── 00_START_HERE.md         # Comece aqui!
│   ├── 01_architecture.md       # Arquitetura
│   ├── 03_mock_server.md        # Mock server
│   └── 04_api_reference.md      # API docs
│
├── src/               # Código de produção
│   ├── olostech_api.py          # Cliente API
│   ├── dashboard.py             # Dashboard gráfico
│   └── utils/                   # Utilitários
│
├── har_tools/         # Ferramentas HAR
│   ├── har_parser.py            # Parser HAR
│   ├── har_extractor_cli.py     # CLI extractor
│   └── har_mock_server.py       # Mock server
│
├── tests/             # Testes organizados
│   ├── unit/                   # Unitários
│   ├── integration/            # Integração
│   ├── e2e/                    # End-to-end
│   └── regression/             # Regressão HAR
│
├── examples/          # Exemplos de uso
│   ├── basic_mock_usage.py     # Mock básico
│   └── mock_server_demo.py     # Demo interativa
│
├── scripts/           # Scripts utilitários
│   ├── run_all_tests.sh        # Executa testes
│   ├── start_mock_server.sh    # Inicia mock
│   └── extract_har.sh          # Extrai HAR
│
└── data/              # Dados HAR
    ├── w6.olostech.com.br.har # HAR original
    └── har_database.json       # Database estruturada
```

## 🎯 Fluxo de Desenvolvimento

### 1. Setup (Primeira vez)

```bash
# Clone o projeto
cd /path/to/Emissor/standalone/olostech_automation

# Extraia dados HAR (se ainda não fez)
./scripts/extract_har.sh data/w6.olostech.com.br.har
```

### 2. Desenvolvimento Offline

```bash
# Inicie mock server
./scripts/start_mock_server.sh

# Desenvolva em outra aba
# python3 examples/basic_mock_usage.py

# Teste enquanto desenvolve
pytest tests/integration/ -v
```

### 3. Validação (quando pronto)

```bash
# Configure credenciais Olostech
cp config/.env.example config/.env
nano config/.env

# Execute E2E tests
pytest tests/e2e/test_professional_workflow.py -v
```

## 📖 Exemplos Rápidos

### Usar Mock Server

```python
from har_tools.har_mock_server import HARMockServer

server = HARMockServer("data/har_database.json", port=5000)
server.start()

# Servidor rodando em http://127.0.0.1:5000
# Desenvolva offline!

server.stop()
```

### API Client com Mock

```python
from src.olostech_api import OlostechAPIClient

# Usa mock server em vez de Olostech real
client = OlostechAPIClient(
    base_url="http://127.0.0.1:5000",
    har_path="data/har_database.json"
)

# Desenvolva offline!
await client.complete_login_flow("username", "password")
profissionais = await client.obter_profissionais(...)
```

### Dashboard Gráfico

```bash
cd standalone/olostech_automation
python3 src/dashboard.py
```

## 🔄 Workflow HAR-Driven

```
Capturar HAR (no trabalho)
         ↓
    Extrair dados
         ↓
   Gerar database
         ↓
  Iniciar mock server
         ↓
Desenvolver offline (em casa!)
         ↓
   Validar (no trabalho)
```

## ⚡ Performance

| Operação | Selenium | API | Mock Server |
|----------|----------|-----|-------------|
| Login | 2-3 min | 5-10s | 1-2s |
| Buscar Profissionais | 30-60s | 3-5s | 0.5s |
| Criar Atendimento | 1-2 min | 5-10s | 1-2s |
| **Total** | **3-5 min** | **30-60s** | **5-10s** |

**Ganho:** 6-10x mais rápido que Selenium!

## 🐛 Troubleshooting

### Mock server não inicia

```bash
# Verifique se database existe
ls data/har_database.json

# Extraia se necessário
./scripts/extract_har.sh data/w6.olostech.com.br.har
```

### Testes falham

```bash
# Execute testes unitários primeiro
pytest tests/unit/ -v

# Verifique conformidade HAR
pytest tests/regression/ -v
```

### Import errors após reorganização

```bash
# Atualize imports conforme nova estrutura
# de: import olostech_api
# para: from src.olostech_api import OlostechAPIClient
```

## 📊 Métricas do Projeto

| Métrica | Valor |
|---------|-------|
| Linhas de código | 3.000+ |
| Testes | 140+ |
| Cobertura HAR | 100% (19/19 funções) |
| Endpoints AJAX | 4 |
| Requisições HAR | 801 |

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Leia [CONTRIBUTING.md](CONTRIBUTING.md)
2. Siga padrões do código (português, type hints, docstrings)
3. Adicione testes para novas funcionalidades
4. Atualize documentação

## 📜 Licença

Mesmo licenciamento que o projeto Emissor principal.

---

**Documentação:** Veja [docs/00_START_HERE.md](docs/00_START_HERE.md) para guia completo.
