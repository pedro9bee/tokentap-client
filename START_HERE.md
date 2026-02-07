# 🚀 Comece Aqui - Tokentap Service Setup

## ⚡ Setup Rápido (2 minutos)

```bash
# 1. Configure auto-start e aliases
./scripts/configure-service.sh setup

# 2. Recarregue o shell
source ~/.zshrc

# 3. Teste!
tokentap-start      # Inicia tudo
tokentap-status     # Verifica status
tokentap-open       # Abre dashboard
```

## 🎯 Novos Aliases Disponíveis

Após executar o setup acima, você terá:

```bash
tokentap-start        # 🟢 Inicia proxy + serviços
tokentap-stop         # 🔴 Para todos os serviços
tokentap-web-start    # 🌐 Inicia só o dashboard
tokentap-web-stop     # 🌐 Para só o dashboard
tokentap-status       # ℹ️  Status dos serviços
tokentap-logs         # 📋 Visualiza logs
tokentap-open         # 🔗 Abre no navegador
```

## 🔍 Seu .zshrc Atual

**Status detectado:**
- ✅ Shell integration presente (linhas 169-173)
- ⚠️  Aliases ausentes (serão adicionados no setup)
- ✅ Posicionamento correto (após Kiro CLI)

## 📚 Documentação Completa

- **Português:** [GUIA_PT.md](GUIA_PT.md) - Guia completo em português
- **English:** [docs/README.md](docs/README.md) - Full documentation
- **Quick Ref:** [docs/INSTALL_QUICKREF.md](docs/INSTALL_QUICKREF.md) - Referência rápida

## 🛠️ Ferramentas Extras

### Revisar Configuração (Interativo)

```bash
./scripts/review-shell.sh
```

Menu com opções para:
- Ver integração atual
- Analisar problemas
- Adicionar/remover configurações
- Criar backups

### Verificar Status do Serviço

```bash
./scripts/configure-service.sh status
```

## 🔄 Auto-Start no Boot

O setup configura o tokentap para iniciar automaticamente quando você ligar o Mac.

**Arquivo criado:** `~/Library/LaunchAgents/com.tokentap.service.plist`

**Logs:** `~/.tokentap/logs/service.log`

**Controle manual:**
```bash
# Desabilitar auto-start
launchctl unload ~/Library/LaunchAgents/com.tokentap.service.plist

# Habilitar auto-start
launchctl load ~/Library/LaunchAgents/com.tokentap.service.plist
```

## 📋 Checklist

- [ ] Executar `./scripts/configure-service.sh setup`
- [ ] Recarregar shell: `source ~/.zshrc`
- [ ] Testar `tokentap-start`
- [ ] Verificar `tokentap-status`
- [ ] Abrir dashboard: `tokentap-open`
- [ ] Ler [GUIA_PT.md](GUIA_PT.md) para detalhes completos

## ❓ Precisa de Ajuda?

1. **Guia completo:** [GUIA_PT.md](GUIA_PT.md)
2. **Documentação:** [docs/README.md](docs/README.md)
3. **Issues:** https://github.com/jmuncor/tokentap/issues

---

**Criado em:** 2026-02-07
**O que mudou:** Service auto-start + 7 aliases + docs reorganizada
