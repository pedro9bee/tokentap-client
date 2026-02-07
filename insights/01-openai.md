# Tokentap - Review Insights (OpenAI/Codex)

## Contexto
Este documento consolida os insights da revisão técnica completa do repositório `tokentap-client`, considerando o objetivo principal do projeto: capturar chamadas de LLM via proxy para contagem de tokens com observabilidade operacional.

## Escopo Revisado
- Arquitetura e fluxo de dados do proxy (mitmproxy -> parser -> MongoDB -> dashboard).
- Parsing dinâmico de providers e fallbacks.
- API web (FastAPI), persistência (MongoDB), frontend e endpoint contracts.
- Scripts de instalação/operação (`install/setup/service/uninstall/diagnose`).
- Coerência entre documentação e implementação.

## Observação de Validação
Os testes automatizados não foram executados nesta sessão por restrições de permissão do ambiente de execução. Os achados abaixo são baseados em análise estática com evidência de código.

## Achados Prioritários

### 1) [Crítico] Proxy e serviços expostos sem proteção
**Impacto:** uso indevido do proxy por terceiros na rede, leitura/remoção de dados e potencial abuso como forward proxy.

**Evidência:**
- `tokentap/proxy.py:689` (`listen_host="0.0.0.0"`).
- `tokentap/proxy.py:701` (`block_global=False`).
- `docker-compose.yml:21` (`8080:8080`).
- `docker-compose.yml:42` (`3000:3000`).
- `docker-compose.yml:8` (`27017:27017`).
- `tokentap/web/app.py:58` (`DELETE /api/events/all` sem autenticação/autorização).

**Recomendação:**
- Default local-only (`127.0.0.1`) para proxy/web/mongo.
- Controle de acesso (token/API key) para endpoints destrutivos e leitura de dados sensíveis.
- Opcional: modo "network-exposed" explícito com aviso de risco.

### 2) [Crítico] Captura/log de payload sensível por padrão
**Impacto:** prompts e respostas podem conter credenciais, dados pessoais e segredos.

**Evidência:**
- `tokentap/proxy.py:210` loga request bruta do Kiro.
- `tokentap/proxy.py:286` loga response bruta do Kiro.
- `tokentap/proxy.py:412` persiste `raw_request` sempre que possível.

**Recomendação:**
- Tornar payload bruto opt-in (`debug_mode`) com TTL de retenção.
- Redaction automática de padrões sensíveis (tokens/chaves/segredos).
- Separar contagem de tokens de captura de conteúdo completo.

### 3) [Crítico] Bug de detecção de provider no rewrite backward-compat
**Impacto:** chamadas reescritas de `localhost` para upstream podem não ser classificadas corretamente e não gerar evento.

**Evidência:**
- `tokentap/proxy.py:65` guarda `host = flow.request.host`.
- `tokentap/proxy.py:86` altera `flow.request.host = upstream`.
- `tokentap/proxy.py:103` detecção ainda usa `host` antigo.

**Recomendação:**
- Recalcular `host` após rewrite ou usar sempre `flow.request.host` na detecção.

### 4) [Alto] Empacotamento incompleto para operação via CLI instalada
**Impacto:** instalação via pacote pode quebrar `tokentap up` por falta de artefatos de runtime.

**Evidência:**
- `tokentap/cli.py:33` depende de `docker-compose.yml`.
- `tokentap/cli.py:46` fallback para caminho local do pacote.
- `pyproject.toml:57` inclui apenas `web/static/**/*` e `providers.json`.
- `tokentap.egg-info/SOURCES.txt` não inclui `docker-compose.yml`, Dockerfiles ou scripts.

**Recomendação:**
- Incluir assets necessários no pacote, ou remover dependência de compose local.
- Adicionar smoke test pós-instalação (PyPI) para validar `tokentap up`.

### 5) [Alto] Divergência entre documentação e API exposta
**Impacto:** usuários tentam endpoints anunciados e recebem erro.

**Evidência:**
- Docs indicam `/api/stats/by-program` e `/api/stats/by-project`: `README.md:309`, `README.md:312`.
- Métodos DB existem: `tokentap/db.py:195`, `tokentap/db.py:235`.
- Endpoints FastAPI não existem em `tokentap/web/app.py` (há `summary`, `by-model`, `over-time`).

**Recomendação:**
- Implementar endpoints faltantes ou corrigir docs imediatamente.

### 6) [Alto] `install.sh` não-portável para `/bin/sh` em ambientes comuns (dash)
**Impacto:** instalação automatizada falha em distribuições Linux com `sh` não-Bash.

**Evidência:**
- `scripts/install.sh:1` usa `#!/bin/sh`.
- `scripts/install.sh:55` usa `trap ... ERR` (não POSIX).

**Recomendação:**
- Migrar para `#!/usr/bin/env bash` com `set -euo pipefail`, ou manter POSIX estrito.

## Achados Relevantes (Médio)

### 7) [Médio] Data filters sem validação robusta
**Impacto:** `date_from/date_to` inválidos podem gerar erro 500.

**Evidência:**
- `tokentap/web/app.py:31` recebe string livre.
- `tokentap/db.py:294` usa `datetime.fromisoformat(...)` sem tratamento.

**Recomendação:**
- Validar com tipos de data/hora no FastAPI/Pydantic e retornar 422.

### 8) [Médio] Retorno incorreto de erro 404 no FastAPI
**Impacto:** contrato HTTP inconsistente para cliente.

**Evidência:**
- `tokentap/web/app.py:54` retorna `({"error": ...}, 404)` estilo Flask.

**Recomendação:**
- Usar `HTTPException(status_code=404, detail="...")`.

### 9) [Médio] Uninstall não remove volumes corretos e marker de shell inconsistente
**Impacto:** lixo operacional e estado residual após uninstall.

**Evidência:**
- Volumes criados: `docker-compose.yml:52` (`tokentap-data`, `mitmproxy-certs`).
- Uninstall remove nomes antigos: `scripts/uninstall.sh:65` (`tokentap-client_mongodb_data`).
- Fallback procura marker não usado pelo install: `scripts/uninstall.sh:97` (`# Added by tokentap`).
- Marker real no CLI: `tokentap/cli.py:321`.

**Recomendação:**
- Padronizar nomes de volume e markers em todos os scripts.

### 10) [Médio] Critério de qualidade do parser com lacuna
**Impacto:** perda de mensagens pode passar despercebida.

**Evidência:**
- `tokentap/proxy.py:492` só rejeita quando `original > 1` e `parsed == 1`; não cobre `parsed == 0`.

**Recomendação:**
- Ajustar regra para detectar qualquer perda relevante (`parsed < original` com tolerância configurável).

### 11) [Médio] Endpoint de lista retorna payload completo
**Impacto:** payload pesado e exposição ampla de dados (`raw_request/raw_response`) no `/api/events`.

**Evidência:**
- `tokentap/db.py:61` faz `find(query)` sem projeção.
- `tokentap/db.py:71` devolve documento inteiro.

**Recomendação:**
- Adicionar projeção para listagem e reservar payload bruto ao endpoint de detalhe.

### 12) [Médio] Wrapper de contexto sem escaping seguro
**Impacto:** JSON inválido para nomes com aspas/caracteres especiais.

**Evidência:**
- `scripts/tokentap-wrapper.sh:49` constrói JSON por heredoc interpolado.

**Recomendação:**
- Gerar JSON com `jq -n` (ou escape robusto) sempre.

## Achados Menores (Baixo)

### 13) [Baixo] Checagem de conflito `HTTPS_PROXY` no `review-shell.sh` está quebrada
**Impacto:** falso negativo na análise de configuração.

**Evidência:**
- `scripts/review-shell.sh:103` usa pipeline com `grep -q` no lado esquerdo.

**Recomendação:**
- Corrigir pipeline (sem `-q` no primeiro grep).

### 14) [Baixo] Versão interna divergente do pacote
**Impacto:** confusão em suporte/diagnóstico.

**Evidência:**
- `tokentap/__init__.py:3` -> `0.3.0`.
- `pyproject.toml:7` -> `0.4.1`.

**Recomendação:**
- Unificar versionamento em fonte única.

### 15) [Baixo] Links quebrados no README raiz
**Impacto:** onboarding degradado.

**Evidência:**
- `README.md` referencia `docs/SERVICE_MANAGEMENT.md`, `docs/PROVIDER_CONFIGURATION.md`, etc., mas os nomes atuais usam prefixos numéricos (`docs/03_...`, `docs/04_...`).

**Recomendação:**
- Atualizar links ou criar aliases/redirects de arquivos.

## Perguntas em Aberto
1. O produto deve operar apenas localmente por padrão (`localhost-only`)?
2. Captura de payload bruto é requisito funcional ou apenas diagnóstico?
3. A instalação oficial suportada é PyPI ou somente source/clone?
4. Endpoint destrutivo sem autenticação (`DELETE /api/events/all`) deve permanecer?

## Práticas Recomendadas (Roadmap)

### Curto prazo (segurança e estabilidade)
1. Fechar exposição de rede por padrão e proteger endpoints sensíveis.
2. Desativar captura bruta por default; habilitar apenas em modo debug.
3. Corrigir bug de detecção de provider após rewrite.
4. Corrigir inconsistências docs vs API.

### Médio prazo (qualidade e operação)
1. Estruturar contrato API com Pydantic estrito (datas, filtros, erros).
2. Implementar projeções e paginação eficiente no endpoint de eventos.
3. Padronizar scripts (`install/uninstall/configure`) e revisar portabilidade POSIX/Bash.
4. Criar testes de integração fim-a-fim: CLI -> proxy -> Mongo -> dashboard.

### Longo prazo (governança de dados)
1. Política de retenção e expurgo de dados sensíveis.
2. Mecanismos de redaction e classificação de risco de payload.
3. Perfis de execução (`dev`, `prod-safe`, `debug-capture`) com defaults seguros.

## Resumo Executivo
O projeto tem uma base técnica sólida para observabilidade de uso de tokens por proxy, mas há riscos críticos de segurança e privacidade no estado atual (exposição de rede e captura de payload sensível), além de alguns desvios importantes entre docs e implementação. A priorização correta é: hardening de exposição, minimização de dados e consistência operacional da distribuição.

