# ⚡ SOLUÇÃO RÁPIDA - Proxy não capturando

## 🎯 Seu Problema

Claude não está sendo capturado pelo proxy porque **as variáveis de ambiente não estão configuradas** no seu shell atual.

## ✅ Solução (escolha uma)

### Opção 1: Ativar na sessão atual (rápido)

No terminal onde você vai usar o Claude:

```bash
eval "$(tokentap shell-init)"
```

### Opção 2: Usar script helper

```bash
source ./scripts/activate-proxy.sh
```

### Opção 3: Abrir novo terminal (recomendado)

Simplesmente abra um novo terminal. As variáveis são carregadas automaticamente.

## 🔍 Verificar se funcionou

```bash
# Deve mostrar: http://127.0.0.1:8080
echo $HTTPS_PROXY
```

Se mostrar o endereço acima, está configurado! ✅

## 🧪 Testar

```bash
# Use o Claude
claude

# Pergunte algo simples
# Depois veja no dashboard
tokentap open
```

## 📊 Status Atual (Diagnóstico)

```
✅ Containers rodando
✅ Proxy respondendo
✅ Web dashboard OK
✅ MongoDB OK
✅ 54 eventos já capturados anteriormente
❌ Variáveis de ambiente NÃO configuradas no shell atual
⚠️  Aliases ausentes
```

## 🚀 Próximos Passos Recomendados

1. **Ativar proxy agora:**
   ```bash
   eval "$(tokentap shell-init)"
   ```

2. **Adicionar aliases convenientes:**
   ```bash
   ./scripts/configure-service.sh setup
   source ~/.zshrc
   ```

3. **Testar com Claude:**
   ```bash
   claude
   ```

4. **Ver dashboard:**
   ```bash
   tokentap-open  # (depois de adicionar aliases)
   # ou
   open http://127.0.0.1:3000
   ```

## 💡 Por que aconteceu?

Você ativou o venv **depois** de abrir o shell.

O `.zshrc` executa `tokentap shell-init` **quando o shell inicia**, não quando ativa venv.

**Soluções permanentes:**
- Sempre abrir novo terminal para usar Claude
- Ou executar `eval "$(tokentap shell-init)"` após ativar venv
- Ou adicionar ao comando de ativação do venv

## 🔧 Scripts Úteis

```bash
# Diagnóstico completo
./scripts/diagnose.sh

# Ativar proxy
source ./scripts/activate-proxy.sh

# Configurar service + aliases
./scripts/configure-service.sh setup

# Revisar shell config
./scripts/review-shell.sh
```

## 📖 Documentação Completa

- [TROUBLESHOOTING_PT.md](TROUBLESHOOTING_PT.md) - Guia completo
- [GUIA_PT.md](GUIA_PT.md) - Guia geral
- [START_HERE.md](START_HERE.md) - Início rápido
