# Future Agents 🇧🇷 — Plano de Evolução (06/03/2026)

> Baseado em pesquisa de mercado realizada em 06/03/2026 via Tavily.
> Contexto: O ecossistema de AI coding teve mudanças massivas desde jan/2026.

---

## 🌍 O Que Mudou no Mercado (Jan–Mar 2026)

| Evento | Impacto no Future Agents |
|:---|:---|
| **Codex reescrito em Rust** (fev/2026) — zero deps, sandbox modes, plugin system | Nosso scheduler precisa de plugin system equivalente |
| **Claude Agent Teams** (fev/2026) — sub-agents com context window dedicado + git worktrees | Podemos adotar worktrees para isolamento de agentes |
| **VS Code 1.109** — multi-agent command center (Copilot + Claude + Codex lado a lado) | Nossa arquitetura já suporta multi-model, mas falta integração IDE |
| **Codex Desktop App** — orquestração visual com Skills marketplace | Nosso DAG precisa de visualização e skills como first-class citizens |
| **MCP virou padrão de facto** — adotado por OpenAI, Microsoft, Google | Future Agents PRECISA ser MCP-native urgentemente |
| **MCP Gateways** aparecem (Bifrost, IBM ContextForge) — registries federados | Oportunidade: publicar nosso scheduler como MCP server |
| **Agent2Agent (A2A)** se consolida junto com MCP | O ecossistema **Loki Mode** (local) já antecipa essa interop |
| **Observabilidade de agentes** (Arize, Braintrust, AgentOps) — métricas compostas | Evoluir o dashboard do **Andru.ia** para incluir OpenTelemetry |

---

## 🎯 6 Melhorias Prioritárias

### 1. 🔌 MCP-Native Architecture

**Por quê:** MCP é agora o padrão universal. OpenAI, Microsoft e Google adotaram. Ficar fora = irrelevância.

**O que fazer:**
- [ ] Expor o Scheduler como um MCP Server (ferramentas: `create_dag`, `dispatch_task`, `get_status`, `approve_merge`)
- [ ] Expor Memory Runtime como MCP Server (ferramentas: `store_fact`, `query_facts`, `get_context`)
- [ ] Criar `mcp.json` config no repositório para discovery automático
- [ ] Suportar tanto `stdio` quanto `HTTP/SSE` transport
- [ ] Registrar no MCP Gateway Registry da comunidade

**Impacto:** Qualquer IDE (VS Code, Cursor, JetBrains) ou agente (Claude Code, Codex) pode consumir o Future Agents como ferramenta.

---

### 2. 🌳 Git Worktrees por Agente

**Por quê:** Claude Agent Teams já usa worktrees para isolamento. Codex App também. É o padrão emergente para evitar conflitos entre agentes paralelos.

**O que fazer:**
- [ ] Cada agente (`planner`, `coder`, `tester`, `reviewer`) opera em seu próprio git worktree
- [ ] O scheduler cria/destrói worktrees automaticamente por DAG
- [ ] Merge de worktrees passa por CI antes de chegar ao branch principal
- [ ] Worktrees registrados como metadata no Redis (`worktree:<agent>:<dag_id>`)

**Impacto:** Agentes podem trabalhar em paralelo de verdade, sem race conditions no filesystem.

---

### 3. 📊 Observabilidade com OpenTelemetry

**Por quê:** O mercado de observabilidade de agentes explodiu (Arize, LangSmith, Braintrust). Nosso `audit_log` é bom, mas não é interoperável.

**O que fazer:**
- [ ] Instrumentar o scheduler com OpenTelemetry traces (spans por task, por agente)
- [ ] Exportar para qualquer backend (Jaeger, Grafana Tempo, Arize)
- [ ] Criar métricas compostas: `task_latency`, `fix_loop_count`, `cost_per_dag`, `model_token_usage`
- [ ] Dashboard Grafana com o DAG pipeline em tempo real
- [ ] Alertas quando `fix_loop_count > 3` ou `cost_per_dag > threshold`

**Impacto:** Visibilidade de produção real. Times podem debugar DAGs como debugam microserviços.

---

### 4. 🧩 Skills como First-Class Citizens

**Por quê:** Codex App lançou Skills marketplace. Claude Code tem installable skills. É o novo paradigma de extensibilidade.

**O que fazer:**
- [ ] Definir formato `skill.json` padronizado para Future Agents
- [ ] Criar diretório `skills/` com skills instaláveis via CLI
- [ ] Skills podem ser invocados pelo scheduler como nós opcionais no DAG
- [ ] Skills publicáveis como MCP tools (double-duty: skill local + MCP server)
- [ ] Skills iniciais: `lint-fix`, `test-generator`, `pr-description`, `security-scan`

**Impacto:** Comunidade pode contribuir skills. Diferenciador forte vs. frameworks fechados.

---

### 5. 🖥️ Visualizador de DAG (Web UI Leve)

**Por quê:** Codex App tem visualização de agentes. LangGraph tem LangGraph Studio. Nós temos... logs no terminal.

**O que fazer:**
- [ ] Web UI minimalista (React + Vite, sem framework pesado)
- [ ] Visualização do DAG em tempo real via Redis Streams SSE
- [ ] Status por nó: 🟢 done, 🟡 running, 🔴 failed, ⚪ pending, 🔵 fix-loop
- [ ] Timeline vertical com logs de cada agente
- [ ] Botão de "Human Approve" integrado na UI (substitui CLI para aprovação)
- [ ] Deploy como container Docker opcional

**Impacto:** Experiência de "control room" que o mercado está exigindo.

---

### 6. 🤝 Agent2Agent (A2A) Interoperability

**Por quê:** O protocolo A2A está se consolidando junto ao MCP. Agentes de sistemas diferentes precisam se comunicar.

**O que fazer:**
- [ ] Implementar A2A Agent Card para o scheduler
- [ ] Expor capabilities via `/.well-known/agent.json`
- [ ] Permitir que agentes externos (Codex, Claude Code) deleguem tasks via A2A
- [ ] Manter o Redis Streams como backbone interno, mas com gateway A2A na borda

**Impacto:** Future Agents se torna o "scheduler universal" — qualquer agente pode submeter trabalho.

---

## 📅 Roadmap Proposto

```
Q1 2026 (Mar)          Q2 2026 (Abr–Jun)          Q3 2026 (Jul–Set)
─────────────          ──────────────────          ──────────────────
✅ README world-class   🔌 MCP Server (Sched)      🤝 A2A Gateway
✅ Hero image            🌳 Git Worktrees            🧩 Skills marketplace
✅ Gitea PR Gate         📊 OpenTelemetry basic      🖥️ DAG Visualizer v2
                        🧩 Skills format v1         📊 Grafana dashboards
                        🖥️ DAG Visualizer v1        🔒 SOC 2 prep
```

---

## 🧭 Princípios Que NÃO Mudam

Mesmo adotando novidades, estes invariantes são sagrados:

1. **Redis Streams é o único bus** — sem Pub/Sub, sem WebSockets entre agentes
2. **CI é autoritativo** — agentes nunca auto-reportam sucesso
3. **Merge requer aprovação humana** — sem exceções
4. **Memória destilada** — raw transcripts rejeitados em runtime
5. **Scheduler é serviço separado** — nunca embedded no agente
6. **Local-first** — código sensível não sai da máquina

---

## 💡 Insight Final

O mercado em março de 2026 está dividido em 3 categorias:

1. **IDE-first** (Cursor, Copilot) — completions inline
2. **Terminal-first** (Claude Code, Codex CLI) — agentes via terminal
3. **Orchestration-first** (Codex App, LangGraph Studio) — "control rooms"

**Future Agents está posicionado para ser a alternativa open-source, local-first e governada da categoria 3.**

### 🏛️ A Base Tecnológica Interna

Para realizar este plano, utilizaremos o poder de fogo já presente no diretório `.agent/skills/`:

1. **Andru.ia Consultant (00):** O cérebro por trás da arquitetura "Diamond Standard". Ele regerá a evolução técnica para garantir que cada novo módulo siga o padrão de excelência de 2026.
2. **Loki Mode (Swarms):** A engine de execução autônoma. O Loki Mode v2.35+ será o responsável por realizar o "Growth Loop" do projeto, operando em swarms de agentes Haiku 4.5 para testes e monitoramento.
3. **Antigravity Workflows:** Nossa camada de orquestração proprietária que une a visão do consultor à execução do Loki.

A vantagem competitiva é clara: somos o único que combina **CI-authoritative + human-approval + event-driven DAG + multi-model routing** em um pacote open-source. O que falta é **MCP, visualização e worktrees** — e este plano cobre isso.
