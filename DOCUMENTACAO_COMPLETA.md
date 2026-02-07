# 📋 Documentação Completa do Projeto Tokentap

## 🔍 Visão Geral

**Tokentap** é uma ferramenta de monitoramento de tokens para APIs de LLM (Large Language Models) que funciona como um proxy MITM (Man-in-the-Middle) transparente. Intercepta tráfego HTTPS para APIs de LLM, captura o uso de tokens de cada requisição/resposta e exibe tudo em um dashboard web.

### Características Principais
- **Proxy Transparente**: Funciona com qualquer ferramenta CLI que respeite `HTTPS_PROXY`
- **Multi-Provider**: Suporta Anthropic, OpenAI, Google Gemini e Amazon Q (Kiro)
- **Dashboard Web**: Interface moderna para visualização de estatísticas
- **Docker**: Configuração completa com containers
- **MongoDB**: Armazenamento persistente de eventos

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    Tokentap Architecture                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CLI Tools (Claude, Codex, Gemini, etc.)                  │
│                    │                                        │
│                    │ HTTPS_PROXY=http://127.0.0.1:8080     │
│                    ▼                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MITM Proxy (Port 8080)                 │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │           TokentapAddon                     │    │   │
│  │  │  • Intercepts HTTPS traffic                 │    │   │
│  │  │  • Parses token usage                       │    │   │
│  │  │  • Stores events in MongoDB                 │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                    │                                        │
│                    │ Forward to upstream APIs               │
│                    ▼                                        │
│  Upstream APIs (api.anthropic.com, api.openai.com, etc.)  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MongoDB (Port 27017)                  │   │
│  │  • Event storage                                   │   │
│  │  • Token usage history                             │   │
│  │  • Request/response metadata                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                    ▲                                        │
│                    │                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Web Dashboard (Port 3000)                │   │
│  │  • FastAPI backend                                 │   │
│  │  • Real-time statistics                            │   │
│  │  • Event history                                   │   │
│  │  • Per-model breakdowns                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
tokentap-client/
├── 📄 README.md                    # Documentação principal
├── 📄 LICENSE                      # Licença MIT
├── 📄 pyproject.toml               # Configuração do projeto Python
├── 📄 docker-compose.yml           # Orquestração dos serviços
├── 📄 Dockerfile.proxy             # Container do proxy
├── 📄 Dockerfile.web               # Container do dashboard web
├── 📄 .gitignore                   # Arquivos ignorados pelo Git
├── 📄 CLAUDE.md                    # Documentação específica do Claude
│
├── 📁 tokentap/                    # Código fonte principal
│   ├── 📄 __init__.py              # Inicialização do pacote
│   ├── 📄 cli.py                   # Interface de linha de comando (559 linhas)
│   ├── 📄 config.py                # Configurações centralizadas (50 linhas)
│   ├── 📄 proxy.py                 # Proxy MITM principal (454 linhas)
│   ├── 📄 proxy_service.py         # Serviço do proxy (22 linhas)
│   ├── 📄 db.py                    # Interface MongoDB (213 linhas)
│   ├── 📄 parser.py                # Parsers de requisições (82 linhas)
│   ├── 📄 response_parser.py       # Parsers de respostas (294 linhas)
│   ├── 📄 dashboard.py             # Dashboard terminal (175 linhas)
│   ├── 📄 web_service.py           # Serviço web (25 linhas)
│   │
│   └── 📁 web/                     # Dashboard web
│       ├── 📄 __init__.py          # Inicialização do módulo web
│       ├── 📄 app.py               # API FastAPI (3348 linhas)
│       └── 📁 static/              # Arquivos estáticos
│           ├── 📄 index.html       # Interface principal
│           ├── 📁 css/             # Estilos CSS
│           └── 📁 js/              # Scripts JavaScript
│
├── 📁 .venv/                       # Ambiente virtual Python
├── 📁 .pytest_cache/              # Cache do pytest
├── 📁 .github/                     # Configurações GitHub
│   └── 📁 workflows/
│       └── 📄 publish.yml          # CI/CD pipeline
│
└── 📁 tokentap.egg-info/           # Metadados do pacote
```

---

## 🧪 Relatório de Testes Completo

### Status dos Serviços ✅
| Serviço | Status | Porta | Saúde |
|---------|--------|-------|-------|
| MongoDB | ✅ Ativo (24+ min) | 27017 | ✅ Healthy |
| Proxy | ✅ Ativo (2+ min) | 8080 | ✅ Healthy |
| Web Dashboard | ✅ Ativo (20+ min) | 3000 | ✅ Healthy |

### Testes de Funcionalidade ✅

#### 1. CLI Interface
- ✅ Comando `tokentap --help` funcional
- ✅ Todos os comandos disponíveis listados
- ✅ Documentação inline clara

#### 2. Conectividade de Serviços
- ✅ Proxy health endpoint: `http://localhost:8080/health`
- ✅ Web API health endpoint: `http://localhost:3000/api/health`
- ✅ Conectividade MongoDB confirmada

#### 3. Importação Python
- ✅ Módulo `tokentap` importa sem erros
- ✅ Todas as dependências resolvidas

#### 4. Dados em Produção
- ✅ **35 eventos** já capturados no banco
- ✅ Estatísticas de uso disponíveis:
  - Total input tokens: 338
  - Total output tokens: 903
  - Cache creation tokens: 776
  - Cache read tokens: 54,480
  - Total requests: 43

---

## 🔧 Análise Técnica Detalhada

### Pontos Fortes ✅

#### 1. Arquitetura Limpa
- **Separação de responsabilidades**: CLI, proxy, database, web API, parsers
- **Módulos focados**: Cada arquivo tem responsabilidade específica
- **Padrões async/await**: Uso adequado para operações I/O

#### 2. Práticas Modernas Python
- **Type hints**: Tipagem em todo o código
- **Pydantic**: Validação de dados
- **FastAPI**: API web com documentação automática
- **Rich**: Interface CLI aprimorada
- **pathlib**: Manipulação moderna de arquivos

#### 3. Configuração Robusta
- **Configuração centralizada**: `config.py`
- **Variáveis de ambiente**: Suporte completo
- **Defaults sensatos**: Valores padrão apropriados

#### 4. Tratamento de Erros
- **Exception handling**: Tratamento abrangente
- **Graceful degradation**: Falhas não críticas
- **Logging**: Sistema de logs adequado

#### 5. Documentação
- **Docstrings**: Documentação clara
- **README estruturado**: Guia completo
- **pyproject.toml**: Metadados corretos

### Áreas de Melhoria ⚠️

#### 1. Cobertura de Testes (CRÍTICO)
- ❌ **Nenhum teste unitário** encontrado
- ❌ **Sem testes de integração** para funcionalidade crítica do proxy
- ❌ **Sem configuração de testes** no pyproject.toml

#### 2. Complexidade de Código
- ⚠️ `cli.py` (559 linhas) muito grande
- ⚠️ `proxy.py` (454 linhas) poderia ser dividido
- ⚠️ Algumas funções excedem tamanho recomendado

#### 3. Recuperação de Erros
- ⚠️ Mecanismos de retry limitados
- ⚠️ Falhas de conexão MongoDB poderiam ser mais robustas
- ⚠️ Falhas de inicialização do proxy precisam de melhor feedback

#### 4. Considerações de Segurança
- ⚠️ Validação de entrada limitada para parâmetros CLI
- ⚠️ Tratamento de certificados poderia ser mais explícito
- ⚠️ Sem rate limiting ou proteção contra abuso

#### 5. Observabilidade
- ⚠️ Logging básico, sem logging estruturado
- ⚠️ Sem coleta de métricas
- ⚠️ Endpoints de health check limitados

---

## 🚀 Comandos Disponíveis

### Comandos Docker (Principais)
| Comando | Descrição |
|---------|-----------|
| `tokentap up` | Inicia proxy + dashboard + MongoDB |
| `tokentap down` | Para todos os serviços |
| `tokentap status` | Mostra status dos serviços |
| `tokentap logs` | Visualiza logs dos serviços |
| `tokentap open` | Abre dashboard no navegador |

### Comandos de Configuração
| Comando | Descrição |
|---------|-----------|
| `tokentap install` | Adiciona integração shell |
| `tokentap uninstall` | Remove integração shell |
| `tokentap shell-init` | Imprime exports de ambiente |
| `tokentap env` | Gera arquivo .env |
| `tokentap install-cert` | Instala CA no keychain |

### Comandos Legacy (Sem Docker)
| Comando | Descrição |
|---------|-----------|
| `tokentap start` | Inicia proxy + dashboard terminal |
| `tokentap claude` | Executa Claude Code via proxy |
| `tokentap codex` | Executa OpenAI Codex via proxy |
| `tokentap gemini` | Executa Gemini CLI via proxy |
| `tokentap run --provider <name> <cmd>` | Executa comando via proxy |

---

## 🔌 Providers Suportados

| Provider | Domínio | Status | Recursos |
|----------|---------|--------|----------|
| **Anthropic** | `api.anthropic.com` | ✅ Suportado | Claude Code, SSE streaming |
| **OpenAI** | `api.openai.com` | ✅ Suportado | Codex, GPT models |
| **Google** | `generativelanguage.googleapis.com` | ✅ Suportado | Gemini CLI |
| **Amazon Q** | `q.*.amazonaws.com` | ✅ Suportado | Kiro CLI |

### Extração de Tokens por Provider
- **Anthropic**: Eventos SSE `message_start`/`message_delta` ou campo `usage` em JSON
- **OpenAI**: Campo `usage` em resposta ou chunks de streaming
- **Gemini**: Campo `usageMetadata`
- **Amazon Q**: Parsing customizado para formato Kiro

---

## 📊 Métricas de Qualidade

### Estatísticas do Código
- **Total de linhas**: 1,877 linhas
- **Módulos principais**: 10 arquivos Python
- **Imports**: 55 declarações de import
- **Complexidade**: Média-alta (alguns arquivos grandes)

### Avaliação Geral: 7.5/10

#### Pontos Positivos (+)
- ✅ Arquitetura bem estruturada
- ✅ Código Python moderno
- ✅ Funcionalidade completa e operacional
- ✅ Documentação adequada
- ✅ Docker setup funcional

#### Pontos Negativos (-)
- ❌ Ausência total de testes automatizados
- ❌ Módulos muito grandes (cli.py, proxy.py)
- ❌ Sem pipeline CI/CD robusto
- ❌ Observabilidade limitada

---

## 🛠️ Recomendações de Melhoria

### Prioridade Alta (Imediato)
1. **Implementar suite de testes** (pytest)
2. **Configurar CI/CD** com testes automatizados
3. **Adicionar ferramentas de qualidade** (black, flake8, mypy)
4. **Dividir módulos grandes** em componentes menores

### Prioridade Média (Curto Prazo)
1. **Logging estruturado** com níveis apropriados
2. **Mecanismos de retry** para operações de rede
3. **Validação de entrada** e sanitização
4. **Endpoints de health check** para todos os serviços

### Prioridade Baixa (Longo Prazo)
1. **Monitoramento de performance** e métricas
2. **Validação de configuração**
3. **Scanning de segurança** e verificação de vulnerabilidades
4. **Estratégia de versionamento** da API

---

## 🔐 Considerações de Segurança

### Certificados MITM
- CA certificate armazenado em `~/.mitmproxy/`
- Instalação opcional no keychain do sistema
- Variáveis de ambiente para certificados SSL

### Variáveis de Ambiente Configuradas
```bash
HTTPS_PROXY=http://127.0.0.1:8080
HTTP_PROXY=http://127.0.0.1:8080
NO_PROXY=localhost,127.0.0.1
NODE_EXTRA_CA_CERTS=~/.mitmproxy/mitmproxy-ca-cert.pem
SSL_CERT_FILE=~/.mitmproxy/mitmproxy-ca-cert.pem
REQUESTS_CA_BUNDLE=~/.mitmproxy/mitmproxy-ca-cert.pem
```

---

## 📈 Dados de Uso Atual

### Estatísticas em Tempo Real
- **Eventos capturados**: 35
- **Requisições processadas**: 43
- **Tokens de entrada**: 338
- **Tokens de saída**: 903
- **Cache creation**: 776 tokens
- **Cache read**: 54,480 tokens

### Providers Ativos
Baseado nos dados capturados, o sistema está interceptando principalmente tráfego do **Kiro CLI** (Amazon Q), demonstrando funcionamento em produção.

---

## 🎯 Conclusão

O **Tokentap** é uma ferramenta robusta e funcional para monitoramento de tokens de LLM. A arquitetura é bem pensada e a implementação demonstra boas práticas de desenvolvimento Python. 

**Principais Sucessos:**
- Sistema completamente operacional
- Arquitetura escalável e modular
- Interface web moderna e funcional
- Suporte multi-provider efetivo

**Próximos Passos Críticos:**
- Implementação de testes automatizados
- Refatoração de módulos grandes
- Melhoria da observabilidade
- Fortalecimento da segurança

O projeto está pronto para uso em produção, mas beneficiaria significativamente de melhorias na qualidade e testabilidade do código.

---

*Documentação gerada em: 07 de Fevereiro de 2026*
*Versão do Tokentap: 0.3.0*
*Status: Operacional em Produção*
