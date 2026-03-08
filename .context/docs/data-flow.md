---
type: doc
name: data-flow
description: How data moves through the system and external integrations
category: data-flow
generated: 2026-03-05
status: active
scaffoldVersion: "2.0.0"
---

# Fluxo de Dados e Integrações

> Snapshot gerado. Não autoritativo.
> Veja [`../../AGENTS.md`](../../AGENTS.md) e os docs canônicos em [`../../docs/`](../../docs/) antes de usar este arquivo como referência operacional.

## Pipeline Principal de Tarefas

O workflow padrão disparado por um evento `issue_created`:

```
Externo/Planner
    │
    │ issue_created → agent_tasks
    ▼
Scheduler (service.py)
    │ constrói DAG, persiste no Redis
    │ despacha plan_task → agent_tasks
    ▼
Agente Planner
    │ task_completed → agent_results
    ▼
Scheduler
    │ despacha implement_task → agent_tasks
    ▼
Agente Coder
    │ task_completed → agent_results
    ▼
Scheduler
    │ despacha test_task → agent_tasks
    ▼
Agente Tester
    │ task_completed → agent_results
    ▼
Scheduler
    │ [aguarda ci_passed em ci_events]
    │ despacha review_task → agent_tasks
    ▼
Agente Reviewer
    │ task_completed → agent_results
    ▼
Scheduler
    │ despacha human_approval_gate
    │ [aguarda aprovação humana confiável]
    │ despacha merge_task
    ▼
Merge completo
```

## Fix Loop em Falha do CI

```
Argo CI
    │ ci_failed → ci_events
    ▼
Scheduler
    │ adiciona fix_task ao DAG
    │ bloqueia todas as tarefas downstream
    │ despacha fix_task → agent_tasks
    ▼
Agente Coder
    │ task_completed → agent_results
    ▼
Scheduler
    │ despacha rerun_ci
    │ [aguarda ci_passed em ci_events]
    ▼
Continua para review_task (se ci_passed)
```

## Redis Streams — Roteamento de Eventos

```
┌─────────────────────────────────────────────────────────┐
│                    Redis Streams                        │
│                                                         │
│  agent_tasks   ──────────────→  Agentes (leitura)       │
│  agent_results ←──────────────  Agentes (escrita)       │
│  ci_events     ←──────────────  Argo CI (escrita)       │
│  memory_events ←──────────────  Agentes/Runtime (escr.) │
│  system_events ←──────────────  Scheduler/Runtime       │
│                                                         │
│  Scheduler lê:    agent_results, ci_events              │
│  Scheduler escreve: agent_tasks, system_events          │
└─────────────────────────────────────────────────────────┘
```

## Estado do DAG no Redis

Cada grafo de workflow escreve nestas chaves Redis:

```
dag:{graph_id}           → metadados do grafo
dag_tasks:{graph_id}     → conjunto de IDs de tarefas no grafo
task:{task_id}           → metadados e payload da tarefa
taskdeps:{task_id}       → lista de dependências da tarefa
taskstatus:{task_id}     → status atual da tarefa
scheduler:metrics        → contadores (tarefas despachadas, completadas, falhas)
scheduler:throughput     → hashes de throughput
```

Registros de dead-letter e IDs de eventos processados também são persistidos no Redis para suportar tratamento idempotente de eventos.

## Caminho de Escrita de Memória

```
Agente/Runtime
    │ memory_write_requested → memory_events
    ▼
Serviço de Runtime de Memória (runtime_service.py)
    │ valida estrutura do MemoryRecord
    │ rejeita logs de conversa brutos
    │ persiste registros aceitos no Redis (escopo projeto/grafo/tarefa)
    │ emite audit_log ou system_alert em rejeição
    ▼
Redis (armazenamento de memória)
```

## Caminho de Auditoria e Alertas

```
Scheduler / Runtime de Memória
    │
    ├── audit_log → system_events   (todas as decisões aceitas/rejeitadas)
    └── system_alert → system_events (apenas falhas críticas)
```

Inspecionar diretamente:

```bash
docker exec redis-integration redis-cli XRANGE system_events - +
```

## Pontos de Integração Externos

| Sistema | Direção | Stream / Mecanismo |
|---------|---------|-------------------|
| Argo CI | Entrada | `ci_events` (autoritativo) |
| Gitea | Fronteira de hospedagem de código | Não conectado ao Redis diretamente |
| Operador humano | Entrada | `agent_results` com metadados de aprovação `source="system"` |
| Gateway de modelos | Interno | `workspace/gateway/` roteia requisições para provedores |

## Docs Relacionados

- [Arquitetura](./architecture.md)
- [Glossário](./glossary.md)
- [Runbook de Validação Local](./local-validation.md)
