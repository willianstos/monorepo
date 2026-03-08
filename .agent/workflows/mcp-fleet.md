# /mcp-fleet
---
description: Converge a configuração de servidores MCP em todas as superfícies — Claude Code CLI, Codex WSL, Codex Windows e Claude Desktop — em uma única execução.
trigger: /mcp-fleet
args: "[--dry-run] [--scope all|windows|wsl|projects|codex|claude-desktop]"
runner: any
version: 3.0.0
---

## O que é

Workflow operacional para convergência em lote dos servidores MCP do home lab.
Aplica e verifica o inventário canônico definido em [`bootstrap/mcp-registry.toml`](../../bootstrap/mcp-registry.toml) nas quatro superfícies:

| Superfície | Arquivo alvo |
|-----------|-------------|
| Claude Code CLI (WSL + AntiGravity) | `~/.claude.json` (via `claude mcp add -s user`) |
| Codex WSL | `~/.codex/config.toml` |
| Codex Windows | `C:\Users\Zappro\.codex\config.toml` |
| Claude Desktop (Windows) | `AppData\Roaming\Claude\claude_desktop_config.json` |

Governança complementar: [`docs/windows11-wsl2-mcp-governance.md`](../../docs/windows11-wsl2-mcp-governance.md).

Escopo explícito: `/mcp-fleet` governa apenas inventário e convergência de servidores MCP. Autenticação de GitHub para `git fetch/push` do espelho não é resolvida por MCP e permanece no fluxo de Git com `gh` + credential helper. Ver [`../../docs/guide_git.md`](../../docs/guide_git.md) e [`../../bootstrap/github-mirror-auth.sh`](../../bootstrap/github-mirror-auth.sh).

## Inventário canônico (P1 — ativos)

Versões pinadas são obrigatórias para dependências externas. Servidores MCP locais do repositório devem usar `bash`/`wsl.exe`, `cd` explícito para a raiz do repo e launchers determinísticos em `bootstrap/`.

| Server | Pacote@versão | Claude Code CLI | Codex WSL | Codex Win | Claude Desktop |
|--------|--------------|:---------------:|:---------:|:---------:|:--------------:|
| `docker` | `workspace.mcp.docker_server` (stdio) | ✓ | ✓ | ✓ `wsl.exe` | ✓ `wsl.exe` |
| `git` | `@cyanheads/git-mcp-server@2.10.0` | ✓ | ✓ | ✓ | ✓ |
| `fetch` | `mcp-server-fetch==2025.4.7` (uvx) / `npx` (Win) | ✓ | ✓ | ✓ | ✓ |
| `redis` | `@modelcontextprotocol/server-redis@2025.4.25` | ✓ | ✓ | ✓ | ✓ |
| `filesystem` | `@modelcontextprotocol/server-filesystem@2026.1.14` | ✓ | ✓ | ✓ | ✓ |
| `context7` | `@upstash/context7-mcp@2.1.2` | ✓ | ✓ | ✓ | ✓ |
| `tavily` | `tavily-mcp@0.2.17` | ✓ | ✓ | ✓ | ✓ |
| `TestSprite` | `@testsprite/testsprite-mcp@0.0.30` | ✓ | ✓ | ✓ | ✓ |
| `chrome-devtools` | `chrome-devtools-mcp@0.19.0` | ✓ | ✓ | ✓ | ✓ |
| `ai-context` | `@ai-coders/context@0.7.1` | ✓ | ✓ | ✓ | ✓ |
| `future-agents-local` | `workspace.mcp.server` (stdio) | ✓ | ✓ | ✓ `wsl.exe` | ✓ `wsl.exe` |

**Nota `future-agents-local` no Claude Desktop:** usa `wsl.exe -d Ubuntu-24.04 bash --noprofile --norc -lc "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-future-agents.sh"` — necessário pois o Desktop roda no Windows.

**Nota `docker` nos clientes Windows:** usa `wsl.exe -d Ubuntu-24.04 bash --noprofile --norc -lc "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-docker.sh"` para garantir acesso ao socket Docker do WSL e concentrar o launch em um wrapper versionado.

## Quando usar

- Ao adicionar ou remover um servidor MCP do inventário.
- Ao bumpar versão de qualquer pacote.
- Após onboarding de novo operador ou nova máquina.
- Para verificar drift entre superfícies sem alterar nada (`--dry-run`).

## Quando não usar

- Para alterar a lógica interna de um servidor MCP (apenas configuração de cliente).
- Quando uma superfície diverge por decisão arquitetural explícita e documentada.
- Para corrigir `git push`/`git fetch` com `403` no espelho GitHub. Isso é autenticação Git/HTTPS, não convergência MCP.

## Comando

```text
/mcp-fleet
/mcp-fleet --dry-run --scope all
/mcp-fleet --scope codex
/mcp-fleet --scope wsl
/mcp-fleet --scope windows
/mcp-fleet --scope projects
/mcp-fleet --scope claude-desktop
```

## Fluxo

1. **Leitura do inventário** — carregar `bootstrap/mcp-registry.toml` e `.agent/rules/MCP_SERVERS.md`.
2. **Verificação por superfície** — para cada alvo no escopo, comparar servidores presentes e versões com o inventário.
3. **Convergência** (se não `--dry-run`):
   - Renderizar `bootstrap/templates/` com `python3 bootstrap/render_mcp_configs.py templates`
   - Codex WSL / Windows / Claude Desktop: reaplicar com `bootstrap/codex-governance-wsl.sh` ou `bootstrap/codex-governance.ps1`
   - Project `.mcp.json`: reaplicar com `bootstrap/render_mcp_configs.py apply --target project_mcp --projects-root ...`
   - Preservar campos não conhecidos nos JSON gerenciados.
4. **Resumo de estado**:
   - Superfícies aplicadas
   - Itens adicionados / atualizados / já alinhados / ignorados
5. **Validação operacional**:
   - `claude mcp list` — confirmar 11 servidores
   - `docker ps` — confirmar socket acessível
   - `redis-cli -h 127.0.0.1 -p 6380 ping` — confirmar Redis (quando stack ativa)

## Guardrails

- **Versões pinadas são obrigatórias** para todos os pacotes com distribuição npm/PyPI estável.
- O GitHub MCP Server oficial, mesmo quando instalado, não substitui `gh auth setup-git` nem corrige transporte Git HTTPS. MCP expõe APIs e contexto para hosts compatíveis; o espelho Git continua usando remotes e credential helper.
- Servidores MCP locais do repositório devem sempre iniciar com `bash --noprofile --norc -lc "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-..."`.
- `future-agents-local` deve ter `startup_timeout_sec = 120`; `docker` e `redis`, `40`.
- Evitar edição direta de `~/.codex/config.toml` e `C:\Users\Zappro\.codex\config.toml`; usar o renderer e os scripts de governança.
- Nunca gravar secrets ou API keys em texto plano nos arquivos alvo — usar `env` inline no TOML/JSON apenas para keys já existentes.
- Se variáveis de ambiente de API key não estiverem presentes, manter valores existentes — nunca forçar criação.
- Não executar push, merge ou gates de PR.
- `postgres` está na P2 — não adicionar até que padrão de injeção de secret via `.env` esteja em uso.
- Para serviços Dockerizados acessados de dentro de containers, usar `172.17.0.1`, não `localhost`. Ver [`.agent/rules/GITEA_NETWORKING.md`](../rules/GITEA_NETWORKING.md).

## Saídas

- Configuração MCP convergida em todas as superfícies do escopo.
- Log de itens divergentes, versões desatualizadas e ações tomadas.
- Zero mudanças em `--dry-run`.

## Checklist de ready

- [ ] `claude mcp list` mostra 11 servidores: `docker`, `git`, `fetch`, `redis`, `filesystem`, `context7`, `tavily`, `TestSprite`, `chrome-devtools`, `ai-context`, `future-agents-local`.
- [ ] `~/.codex/config.toml` (WSL) tem os 11 servidores com versões pinadas.
- [ ] `C:\Users\Zappro\.codex\config.toml` tem os 11 servidores com versões pinadas.
- [ ] `C:\Users\Zappro\.codex\config.json`, se existir, está alinhado com o inventário gerado do registro MCP.
- [ ] `claude_desktop_config.json` tem os 11 servidores; `future-agents-local` e `docker` usam `wsl.exe`.
- [ ] `bootstrap/templates/` foi regenerado a partir de `bootstrap/mcp-registry.toml`.
- [ ] Nenhuma dependência externa ficou sem versão pinada.
- [ ] Nenhum secret novo gravado em texto plano.
- [ ] `docker ps` executa sem erro de socket.
