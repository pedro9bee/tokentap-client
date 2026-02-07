# Guia de Configuração Tokentap (Português)

## Resumo das Mudanças

Implementei as seguintes funcionalidades conforme solicitado:

### ✅ 1. Pasta `docs/` Criada

Toda a documentação foi reorganizada em `docs/`:

```
docs/
├── README.md                    - Índice da documentação
├── INSTALL_QUICKREF.md          - Referência rápida de instalação
├── INSTALLATION_SCRIPTS.md      - Detalhes técnicos
├── SCRIPTS.md                   - Referência dos scripts
├── BEFORE_AFTER.md             - Comparação de experiência
└── CHANGES.md                   - Log de mudanças
```

**Todas as referências foram atualizadas:**
- Links para `../scripts/` (relativo à pasta docs)
- Documentação cross-referenced
- README.md principal atualizado com seção "Documentation"

### ✅ 2. Serviço Auto-Inicializável

**Novo script:** `scripts/configure-service.sh`

Este script configura o tokentap para iniciar automaticamente com o computador:

- **macOS:** Cria arquivo launchd plist
- **Linux:** Cria serviço systemd
- **Logs:** Centralizado em `~/.tokentap/logs/`

### ✅ 3. Aliases Convenientes

7 novos aliases para controle rápido:

| Alias | O que faz |
|-------|-----------|
| `tokentap-start` | Inicia proxy e todos os serviços |
| `tokentap-stop` | Para todos os serviços |
| `tokentap-web-start` | Inicia apenas o dashboard web |
| `tokentap-web-stop` | Para apenas o dashboard web |
| `tokentap-status` | Verifica status dos serviços |
| `tokentap-logs` | Visualiza logs |
| `tokentap-open` | Abre dashboard no navegador |

### ✅ 4. Script Interativo de Revisão

**Novo script:** `scripts/review-shell.sh`

Ferramenta interativa para analisar e gerenciar a configuração do shell:
- Visualiza integração atual
- Analisa problemas
- Adiciona/atualiza configurações
- Cria backups automáticos

### ✅ 5. Análise do Seu .zshrc

Analisei seu arquivo `.zshrc` e encontrei:

```
✓ Shell integration presente (linhas 169-173)
⚠ Aliases de conveniência ausentes
✓ Posicionamento correto (após bloco Kiro CLI post)
```

## Para o Seu Caso Específico

### Passo 1: Configurar Serviço e Aliases

```bash
cd /Users/pedrofernandes/management/tokentap-client
./scripts/configure-service.sh setup
```

Isso vai:
1. Criar serviço launchd para auto-start no boot
2. Adicionar os 7 aliases ao seu `.zshrc`
3. Manter o posicionamento correto (após Kiro CLI)

### Passo 2: Recarregar Shell

```bash
source ~/.zshrc
```

### Passo 3: Testar

```bash
# Iniciar serviços
tokentap-start

# Verificar status
tokentap-status

# Abrir dashboard
tokentap-open

# Parar serviços
tokentap-stop
```

## Funcionalidade dos Aliases

### `tokentap-start`
- Executa `tokentap up`
- Inicia: proxy (porta 8080), web dashboard (porta 3000), MongoDB
- Mostra mensagem de sucesso

### `tokentap-stop`
- Executa `tokentap down`
- Para todos os containers Docker
- Mantém dados persistidos em volumes

### `tokentap-web-start`
- Inicia apenas o container web
- Útil quando proxy já está rodando mas web parou
- Mostra URL do dashboard

### `tokentap-web-stop`
- Para apenas o container web
- Proxy continua rodando
- Útil para economizar recursos

### `tokentap-status`
- Mostra status de todos os serviços
- Verifica containers Docker
- Mostra portas em uso

### `tokentap-logs`
- Visualiza logs de todos os serviços
- Útil para debugging
- Pode especificar serviço: `tokentap logs proxy`

### `tokentap-open`
- Abre `http://127.0.0.1:3000` no navegador padrão
- Atalho rápido para dashboard

## Auto-Start no Boot (macOS)

### Como Funciona

O script criou: `~/Library/LaunchAgents/com.tokentap.service.plist`

Esse arquivo diz ao macOS para executar `tokentap up` quando você faz login.

### Controle Manual

```bash
# Carregar serviço (ativar auto-start)
launchctl load ~/Library/LaunchAgents/com.tokentap.service.plist

# Descarregar serviço (desativar auto-start)
launchctl unload ~/Library/LaunchAgents/com.tokentap.service.plist

# Verificar se está carregado
launchctl list | grep tokentap
```

### Logs do Serviço

```bash
# Ver logs
cat ~/.tokentap/logs/service.log

# Ver erros
cat ~/.tokentap/logs/service.error.log

# Acompanhar em tempo real
tail -f ~/.tokentap/logs/service.log
```

## Script Interativo de Revisão

Para revisar e ajustar sua configuração:

```bash
./scripts/review-shell.sh
```

**Menu interativo:**
```
1) Ver integração atual          - Mostra configuração no .zshrc
2) Ver configuração recomendada  - Mostra exemplo completo
3) Analisar configuração         - Detecta problemas
4) Adicionar/atualizar integração
5) Adicionar aliases            - Adiciona os 7 aliases
6) Remover toda configuração    - Limpeza completa
7) Criar backup
8) Abrir .zshrc no editor
9) Sair
```

## Estrutura de Arquivos

### Antes
```
tokentap-client/
├── scripts/
│   ├── common.sh
│   ├── setup.sh
│   ├── install.sh
│   ├── uninstall.sh
│   └── README.md
├── INSTALLATION_SCRIPTS.md
├── INSTALL_QUICKREF.md
├── BEFORE_AFTER.md
└── README.md
```

### Depois
```
tokentap-client/
├── scripts/
│   ├── common.sh
│   ├── setup.sh
│   ├── install.sh
│   ├── uninstall.sh
│   ├── configure-service.sh      ← NOVO
│   └── review-shell.sh            ← NOVO
├── docs/                          ← NOVA PASTA
│   ├── README.md
│   ├── INSTALL_QUICKREF.md
│   ├── INSTALLATION_SCRIPTS.md
│   ├── SCRIPTS.md
│   ├── BEFORE_AFTER.md
│   └── CHANGES.md                 ← NOVO
├── GUIA_PT.md                     ← ESTE ARQUIVO
└── README.md                      ← ATUALIZADO
```

## Verificação da Configuração

### Verificar Integração Shell

```bash
# Ver linhas com tokentap no .zshrc
grep -n tokentap ~/.zshrc

# Verificar variáveis de ambiente
echo $HTTPS_PROXY          # Deve ser: http://127.0.0.1:8080
echo $SSL_CERT_FILE        # Deve apontar para ~/.mitmproxy/...
```

### Verificar Aliases

```bash
# Listar aliases do tokentap
alias | grep tokentap

# Deve mostrar os 7 aliases
```

### Verificar Serviço

```bash
# Status do serviço
./scripts/configure-service.sh status

# Ou manualmente no macOS
launchctl list | grep tokentap
```

## Casos de Uso

### Uso Diário

```bash
# Manhã - iniciar tudo
tokentap-start

# Durante o dia - verificar
tokentap-status

# Ver dashboard
tokentap-open

# Noite - parar tudo
tokentap-stop
```

### Economizar Recursos

```bash
# Manter proxy rodando, parar apenas web
tokentap-web-stop

# Quando precisar do dashboard
tokentap-web-start
```

### Debugging

```bash
# Ver o que está acontecendo
tokentap-logs

# Ver logs em tempo real
tokentap logs -f

# Ver apenas erros
tokentap logs proxy 2>&1 | grep ERROR
```

## Solução de Problemas

### Aliases não funcionam

```bash
# Verificar se foram adicionados
grep tokentap-start ~/.zshrc

# Se não existirem, adicionar
./scripts/configure-service.sh setup

# Recarregar shell
source ~/.zshrc
```

### Serviço não inicia no boot

```bash
# Verificar se está carregado
launchctl list | grep tokentap

# Se não estiver, carregar
launchctl load ~/Library/LaunchAgents/com.tokentap.service.plist
```

### Conflito de portas

```bash
# Ver o que está usando porta 8080
lsof -i :8080

# Ver o que está usando porta 3000
lsof -i :3000

# Parar processo conflitante
kill <PID>
```

## Desinstalar

### Remover Serviço e Aliases

```bash
./scripts/configure-service.sh remove
```

### Remover Tudo (Completo)

```bash
./scripts/uninstall.sh

# Segue prompts interativos para:
# - Parar serviços
# - Remover volumes (dados)
# - Remover integração shell
# - Remover aliases
# - Remover venv
# - Remover certificado CA
```

## Próximos Passos

1. **Executar configuração:**
   ```bash
   ./scripts/configure-service.sh setup
   source ~/.zshrc
   ```

2. **Testar aliases:**
   ```bash
   tokentap-start
   tokentap-status
   ```

3. **Verificar auto-start:**
   - Fazer logout/login
   - Verificar se serviços iniciam automaticamente
   - Checar logs em `~/.tokentap/logs/`

4. **Explorar documentação:**
   ```bash
   # Ler documentação completa
   cat docs/README.md

   # Ver guia de scripts
   cat docs/SCRIPTS.md
   ```

## Perguntas Frequentes

**P: Os aliases sobrescrevem comandos nativos do tokentap?**
R: Não, são aliases separados. `tokentap up` continua funcionando normalmente. Os aliases são apenas atalhos convenientes.

**P: O serviço vai consumir recursos o tempo todo?**
R: Não. O serviço apenas inicia os containers Docker no boot. Você pode pará-los com `tokentap-stop` quando não estiver usando.

**P: Posso usar apenas os aliases sem o auto-start?**
R: Sim! Basta rodar `./scripts/review-shell.sh` e escolher opção 5 para adicionar apenas os aliases.

**P: E se eu usar bash em vez de zsh?**
R: Os scripts detectam automaticamente seu shell e configuram o arquivo correto (.bashrc ou .zshrc).

**P: Os aliases funcionam em todos os terminais?**
R: Sim, após recarregar o shell com `source ~/.zshrc`, funcionam em qualquer novo terminal aberto.

## Suporte

- **Documentação completa:** `docs/README.md`
- **Troubleshooting:** `README.md#troubleshooting`
- **Issues:** https://github.com/jmuncor/tokentap/issues

---

Criado em: 2026-02-07
Versão: 0.4.0
