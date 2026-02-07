# Próximos Passos para Validação

Este documento contém os comandos necessários para validar as alterações implementadas na versão 0.4.0 do Tokentap.

## 1. Verificar Instalação e Dependências

```bash
# Navegar para o diretório do projeto
cd /Users/pedrofernandes/management/tokentap-client

# Ativar virtual environment (se não estiver ativo)
source .venv/bin/activate

# Instalar/atualizar dependências
pip install -e ".[dev]"

# Verificar que jsonpath-ng foi instalado
pip list | grep jsonpath-ng
```

**Resultado esperado**: `jsonpath-ng` deve aparecer na lista de pacotes instalados.

## 2. Testar Configuração Dinâmica de Providers

```bash
# Verificar que o arquivo providers.json existe
ls -la tokentap/providers.json

# Validar JSON (deve retornar conteúdo formatado)
cat tokentap/providers.json | python3 -m json.tool | head -20

# Testar carregamento da configuração
python3 -c "from tokentap.provider_config import get_provider_config; config = get_provider_config(); print(f'Providers carregados: {list(config.providers.keys())}')"
```

**Resultado esperado**:
- Arquivo `providers.json` existe
- JSON é válido
- Providers carregados incluem: anthropic, openai, gemini, kiro, unknown

## 3. Testar Parser Genérico

```bash
# Testar generic parser
python3 << 'EOF'
from tokentap.provider_config import get_provider_config
from tokentap.generic_parser import GenericParser

config = get_provider_config()
parser = GenericParser(config)

# Simular requisição Anthropic
request = {
    "model": "claude-sonnet-4",
    "messages": [{"role": "user", "content": "Hello"}]
}

result = parser.parse_request("anthropic", request)
print(f"✓ Request parsing OK: model={result['model']}, messages={len(result['messages'])}")

# Simular resposta Anthropic
response = {
    "model": "claude-sonnet-4",
    "usage": {
        "input_tokens": 10,
        "output_tokens": 20
    }
}

result = parser.parse_response("anthropic", response, is_streaming=False)
print(f"✓ Response parsing OK: in={result['input_tokens']}, out={result['output_tokens']}")
EOF
```

**Resultado esperado**: Ambas as linhas com ✓ devem aparecer.

## 4. Verificar Scripts de Serviço

```bash
# Verificar que os scripts foram criados
ls -la scripts/service-manager.sh
ls -la scripts/tokentap-wrapper.sh

# Verificar permissões de execução
stat -f "%A %N" scripts/service-manager.sh scripts/tokentap-wrapper.sh
```

**Resultado esperado**: Ambos os scripts devem ter permissão de execução (755).

## 5. Testar Comandos do CLI

```bash
# Verificar help do comando service
python3 -m tokentap.cli service --help

# Verificar comando reload-config existe
python3 -m tokentap.cli reload-config --help 2>&1 | head -5
```

**Resultado esperado**: Comandos devem exibir help sem erros.

## 6. Verificar Documentação

```bash
# Listar documentação numerada
ls -la docs/*_*.md

# Verificar que todos os documentos existem
for doc in 01_QUICK_START 02_INSTALLATION 03_SERVICE_MANAGEMENT 04_PROVIDER_CONFIGURATION 05_CONTEXT_METADATA 06_DEBUGGING_NEW_PROVIDERS 07_TROUBLESHOOTING 10_CLI_REFERENCE 11_ARCHITECTURE; do
    if [ -f "docs/${doc}.md" ]; then
        echo "✓ docs/${doc}.md existe"
    else
        echo "✗ docs/${doc}.md NÃO ENCONTRADO"
    fi
done

# Verificar CHANGES.md atualizado
head -30 docs/CHANGES.md
```

**Resultado esperado**: Todos os documentos devem existir e CHANGES.md deve mostrar versão 0.4.0.

## 7. Teste Integração - Iniciar Serviços

```bash
# Parar serviços se estiverem rodando
tokentap down

# Iniciar serviços com rebuild
tokentap up --build

# Aguardar 10 segundos
sleep 10

# Verificar status
tokentap status
```

**Resultado esperado**: Três containers devem estar rodando (proxy, web, mongodb).

## 8. Teste do Proxy com Configuração Dinâmica

```bash
# Verificar health check do proxy
curl -x http://127.0.0.1:8080 http://localhost/health

# Fazer requisição de teste simulada
# (apenas se tiver claude instalado e configurado)
# export HTTPS_PROXY=http://127.0.0.1:8080
# claude "test" --no-prompt
```

**Resultado esperado**: Health check deve retornar `{"status":"ok","proxy":true}`.

## 9. Verificar MongoDB e Schema

```bash
# Conectar ao MongoDB e verificar schema
docker exec -it tokentap-client-mongodb-1 mongosh tokentap --quiet --eval '
    // Verificar indexes
    print("\n=== Indexes ===");
    db.events.getIndexes().forEach(idx => print(JSON.stringify(idx.key)));

    // Verificar se há eventos (pode estar vazio se é instalação nova)
    print("\n=== Contagem de Eventos ===");
    print("Total eventos: " + db.events.countDocuments());
'
```

**Resultado esperado**:
- Deve mostrar indexes incluindo os novos: `context.program_name`, `context.project_name`, etc.
- Contagem pode ser 0 se for instalação nova

## 10. Teste de Reload de Configuração

```bash
# Criar configuração de usuário customizada
mkdir -p ~/.tokentap
cat > ~/.tokentap/providers.json << 'EOF'
{
  "version": "1.0",
  "capture_mode": "known_only",
  "providers": {}
}
EOF

# Recarregar configuração
tokentap reload-config

# Verificar logs para confirmar reload
tokentap logs proxy | tail -20
```

**Resultado esperado**: Comando deve executar sem erros.

## 11. Teste do Wrapper de Contexto

```bash
# Testar wrapper script
./scripts/tokentap-wrapper.sh "test-script" echo "Testing context wrapper"

# Verificar que TOKENTAP_CONTEXT foi exportado
./scripts/tokentap-wrapper.sh "test" bash -c 'echo $TOKENTAP_CONTEXT | python3 -m json.tool'
```

**Resultado esperado**:
- Primeiro comando deve executar `echo`
- Segundo deve mostrar JSON com `program_name: "test"` e `project_name` com o nome do diretório atual

## 12. Verificar Compatibilidade Retroativa

```bash
# Testar que parsers antigos ainda funcionam
python3 << 'EOF'
from tokentap.response_parser import parse_response, parse_sse_stream

# Teste parser Anthropic legacy
data = {"usage": {"input_tokens": 10, "output_tokens": 20}, "model": "claude"}
result = parse_response("anthropic", data)
print(f"✓ Legacy Anthropic parser OK: {result['input_tokens']} tokens")

# Teste parser OpenAI legacy
data = {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}
result = parse_response("openai", data)
print(f"✓ Legacy OpenAI parser OK: {result['input_tokens']} tokens")

# Teste parser Gemini legacy
data = {"usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20}}
result = parse_response("gemini", data)
print(f"✓ Legacy Gemini parser OK: {result['input_tokens']} tokens")
EOF
```

**Resultado esperado**: Três linhas com ✓ devem aparecer.

## 13. Limpeza Pós-Teste

```bash
# Remover configuração de teste
rm -f ~/.tokentap/providers.json

# Parar serviços (opcional)
# tokentap down

# Desativar virtual environment (opcional)
# deactivate
```

## Checklist de Validação

Marque conforme completa cada item:

- [ ] 1. Dependências instaladas (jsonpath-ng presente)
- [ ] 2. providers.json carrega corretamente
- [ ] 3. GenericParser funciona
- [ ] 4. Scripts têm permissões corretas
- [ ] 5. Comandos CLI funcionam
- [ ] 6. Documentação completa e numerada
- [ ] 7. Serviços Docker iniciam
- [ ] 8. Health check do proxy OK
- [ ] 9. MongoDB com indexes corretos
- [ ] 10. Reload de configuração funciona
- [ ] 11. Wrapper de contexto funciona
- [ ] 12. Parsers legacy funcionam
- [ ] 13. Limpeza concluída

## Troubleshooting

### Erro ao instalar dependências

```bash
# Atualizar pip
pip install --upgrade pip

# Reinstalar com verbose
pip install -e ".[dev]" -v
```

### Serviços Docker não iniciam

```bash
# Verificar Docker está rodando
docker ps

# Ver logs detalhados
docker compose logs

# Rebuild forçado
tokentap down
docker compose build --no-cache
tokentap up
```

### Testes Python falham

```bash
# Verificar PYTHONPATH
export PYTHONPATH=/Users/pedrofernandes/management/tokentap-client:$PYTHONPATH

# Verificar imports
python3 -c "import tokentap; print(tokentap.__file__)"
```

## Próximas Ações Após Validação

1. **Commit das alterações**:
   ```bash
   git add .
   git commit -m "feat: Add dynamic provider config, service management, and context tracking (v0.4.0)"
   ```

2. **Atualizar versão**:
   ```bash
   # Editar pyproject.toml e mudar version = "0.4.0"
   ```

3. **Criar tag de versão**:
   ```bash
   git tag -a v0.4.0 -m "Release v0.4.0: Dynamic config + service management + context tracking"
   git push origin v0.4.0
   ```

4. **Publicar** (opcional):
   ```bash
   python -m build
   twine upload dist/*
   ```

## Recursos Adicionais

- **Documentação completa**: `docs/README.md`
- **Changelog**: `docs/CHANGES.md`
- **Arquitetura**: `docs/11_ARCHITECTURE.md`
- **Troubleshooting**: `docs/07_TROUBLESHOOTING.md`
