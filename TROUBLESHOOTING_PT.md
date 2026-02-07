# 🔧 Troubleshooting Rápido - Tokentap

## 🚨 Problema: Claude/LLM não está sendo capturado

### Sintoma
- Você usa Claude/Codex/Gemini
- Nada aparece no dashboard
- Banco de dados não recebe eventos

### Causa Mais Comum
**Variáveis de ambiente não configuradas no shell atual.**

### ✅ Solução Rápida

**Opção 1: Ativar proxy manualmente (sessão atual)**
```bash
eval "$(tokentap shell-init)"
```

**Opção 2: Usar script helper**
```bash
source ./scripts/activate-proxy.sh
```

**Opção 3: Abrir novo terminal**
```bash
# Abra um novo terminal - as variáveis são carregadas automaticamente
```

### 🔍 Verificar se funcionou

```bash
# Deve mostrar: http://127.0.0.1:8080
echo $HTTPS_PROXY

# Deve mostrar o caminho do certificado
echo $SSL_CERT_FILE

# Ou use o script de diagnóstico
./scripts/diagnose.sh
```

## 📋 Diagnóstico Completo

Execute o script de diagnóstico para identificar problemas:

```bash
./scripts/diagnose.sh
```

O script verifica:
1. ✅ Containers Docker rodando
2. ✅ Variáveis de ambiente configuradas
3. ✅ Conectividade do proxy
4. ✅ Integração shell presente
5. ✅ Certificado SSL válido
6. ✅ Conexão MongoDB

## 🐛 Problemas Comuns

### 1. "Variáveis não configuradas"

**Problema:**
```
HTTPS_PROXY: ❌ NÃO CONFIGURADO
SSL_CERT_FILE: ❌ NÃO CONFIGURADO
```

**Causa:**
- Ativou venv depois de abrir o shell
- Shell não foi recarregado após instalação
- `.zshrc` não tem a integração

**Solução:**
```bash
# Temporário (sessão atual)
eval "$(tokentap shell-init)"

# Permanente (verificar integração)
grep "tokentap shell-init" ~/.zshrc

# Se não existir, adicionar
tokentap install
source ~/.zshrc
```

### 2. "Proxy não está respondendo"

**Problema:**
```
❌ Proxy NÃO está respondendo na porta 8080
```

**Causa:**
- Containers não estão rodando
- Porta 8080 em uso por outro serviço

**Solução:**
```bash
# Verificar containers
docker ps | grep tokentap

# Se não estiverem rodando
tokentap up

# Verificar porta 8080
lsof -i :8080

# Se houver conflito, matar processo
kill <PID>
```

### 3. "Web dashboard não carrega"

**Problema:**
```
❌ Web dashboard: FAILED
```

**Causa:**
- Container web não está rodando
- Porta 3000 em uso

**Solução:**
```bash
# Verificar container web
docker ps | grep web

# Reiniciar apenas web
docker restart tokentap-client-web-1

# Ver logs
tokentap logs web
```

### 4. "MongoDB connection failed"

**Problema:**
```
❌ MongoDB connection: FAILED
```

**Causa:**
- Container MongoDB não iniciou
- Problemas de volume

**Solução:**
```bash
# Ver logs do MongoDB
tokentap logs mongodb

# Reiniciar MongoDB
docker restart tokentap-client-mongodb-1

# Se persistir, recriar volumes
tokentap down
docker volume rm tokentap-client_mongodb_data
tokentap up
```

### 5. "Events in database: 0"

**Problema:**
Tudo parece OK mas eventos = 0

**Causa:**
- Proxy não está interceptando
- Variáveis de ambiente não estão ativas
- Claude/LLM não está usando proxy

**Solução:**
```bash
# 1. Verificar variáveis
./scripts/diagnose.sh

# 2. Ativar proxy se necessário
eval "$(tokentap shell-init)"

# 3. Testar com Claude
claude

# 4. Verificar logs do proxy
tokentap logs proxy | tail -50

# Deve mostrar algo como:
# "Intercepting request to api.anthropic.com"
```

### 6. "SSL certificate verify failed"

**Problema:**
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Causa:**
- Certificado não está trusted system-wide
- Ferramenta não respeita `SSL_CERT_FILE`

**Solução:**
```bash
# Instalar certificado system-wide
tokentap install-cert

# Verificar se foi instalado
security find-certificate -c "mitmproxy"

# macOS: Ver no Keychain Access
open /Applications/Utilities/Keychain\ Access.app
# Procurar por "mitmproxy"
```

## 🔍 Debug Avançado

### Ver logs do proxy em tempo real

```bash
tokentap logs proxy -f
```

### Ver requisições interceptadas

```bash
docker exec -it tokentap-client-proxy-1 sh
cd /root/.mitmproxy/
ls -la
```

### Testar proxy manualmente

```bash
# Testar health endpoint
curl -v -x http://127.0.0.1:8080 http://localhost/health

# Testar com API real (exemplo)
curl -v -x http://127.0.0.1:8080 \
  --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem \
  https://api.anthropic.com/v1/messages
```

### Verificar quantos eventos no banco

```bash
docker exec tokentap-client-mongodb-1 mongosh tokentap --quiet \
  --eval "db.events.countDocuments()"

# Ver últimos eventos
docker exec tokentap-client-mongodb-1 mongosh tokentap --quiet \
  --eval "db.events.find().sort({_id:-1}).limit(5).pretty()"
```

## 📱 Workflow de Debug

1. **Diagnóstico completo**
   ```bash
   ./scripts/diagnose.sh
   ```

2. **Se variáveis não configuradas**
   ```bash
   eval "$(tokentap shell-init)"
   echo $HTTPS_PROXY  # Verificar
   ```

3. **Usar Claude/LLM**
   ```bash
   claude
   # Fazer uma pergunta simples
   ```

4. **Verificar logs em tempo real**
   ```bash
   # Terminal 1
   tokentap logs proxy -f

   # Terminal 2
   claude
   ```

5. **Verificar banco de dados**
   ```bash
   ./scripts/diagnose.sh
   # Olhar "Events in database"
   ```

6. **Ver no dashboard**
   ```bash
   tokentap open
   # Refresh da página
   ```

## 🎯 Checklist de Verificação

Antes de reportar um bug, verifique:

- [ ] Containers rodando: `docker ps | grep tokentap`
- [ ] Variáveis configuradas: `echo $HTTPS_PROXY`
- [ ] Proxy respondendo: `curl -x http://127.0.0.1:8080 http://localhost/health`
- [ ] Dashboard acessível: `curl http://127.0.0.1:3000`
- [ ] Certificado válido: `openssl x509 -noout -in ~/.mitmproxy/mitmproxy-ca-cert.pem`
- [ ] MongoDB conectando: `./scripts/diagnose.sh`
- [ ] Shell integration presente: `grep tokentap ~/.zshrc`
- [ ] Logs sem erros: `tokentap logs`

## 🆘 Ainda com problemas?

1. **Ver logs completos:**
   ```bash
   tokentap logs > tokentap-debug.log
   ```

2. **Executar diagnóstico:**
   ```bash
   ./scripts/diagnose.sh > tokentap-diag.log
   ```

3. **Reportar issue:**
   - GitHub: https://github.com/jmuncor/tokentap/issues
   - Incluir: `tokentap-debug.log` e `tokentap-diag.log`
   - Descrever: OS, shell, o que estava fazendo

## 💡 Dicas

- **Sempre abra um novo terminal** após instalar/configurar
- **Use `./scripts/diagnose.sh`** como primeiro passo
- **Monitore logs** durante uso: `tokentap logs proxy -f`
- **Aliases facilitam:** `tokentap-start`, `tokentap-status`, etc.
- **Dashboard em tempo real:** Deixe aberto e refresh
