---
type: doc
name: architecture
description: System architecture, layers, patterns, and design decisions
category: architecture
generated: 2026-03-05
status: active
scaffoldVersion: "2.0.0"
---

# Arquitetura

> Snapshot gerado. Não autoritativo.
> Veja [`../../AGENTS.md`](../../AGENTS.md) e [`../../docs/architecture.md`](../../docs/architecture.md) como fontes canônicas.

## Visão Geral

Este workspace utiliza uma arquitetura local-first e orientada a eventos para entrega de software assistida por IA.

**Decisões arquiteturais fixas:**

- O scheduler é um serviço separado
- Redis Streams é o único barramento de orquestração
- Estado do DAG é persistido no Redis
- Agentes se comunicam apenas por eventos
- CI é a fonte da verdade para validade do código
- Merge para `main` requer aprovação humana

**Fonte canônica:** `docs/architecture.md`

## Agentes Ativos

Apenas quatro agentes de IA participam da orquestração:

| Agente | Streams Utilizados | Responsabilidade |
|--------|-------------------|-----------------|
| Planner | lê `agent_tasks`, escreve `agent_results` | Interpreta requisições, produz insumos de planejamento |
| Coder | lê `agent_tasks`, escreve `agent_results` | Escreve apenas código de implementação |
| Tester | lê `agent_tasks`, escreve `agent_results` | Possui testes e fixtures apenas |
| Reviewer | lê `agent_tasks`, escreve `agent_results` | Valida qualidade, consistência e guardrails |

Não existem chamadas diretas entre agentes. Toda coordenação passa pelo scheduler via Redis Streams.

## Modelo de Orquestração

O scheduler (`workspace/scheduler/service.py`) possui toda a coordenação entre agentes. É stateless por contrato e reconstrói o estado do workflow a partir do Redis a cada evento.

Responsabilidades do scheduler:

1. Escuta Redis Streams via consumer groups
2. Constrói DAGs a partir de eventos `issue_created` ou `task_graph_created`
3. Persiste estado do DAG e das tarefas no Redis
4. Despacha tarefas prontas (apenas após dependências completarem)
5. Valida ownership de tarefas e transições de status antes de mutar estado
6. Aplica guardrails antes do dispatch e após resultados das tarefas
7. Bloqueia tarefas CI-gated até o CI passar
8. Bloqueia merge até a aprovação humana ser registrada
9. Reage a eventos do Argo CI em `ci_events`
10. Cria fix loops após falha do CI
11. Emite `system_alert` em falha crítica ou esgotamento de retries
12. Emite `audit_log` em todas as decisões de orquestração aceitas e rejeitadas

## Redis Streams

Os únicos streams suportados:

| Stream | Finalidade |
|--------|-----------|
| `agent_tasks` | Itens de trabalho despachados para agentes |
| `agent_results` | Resultados de conclusão dos agentes |
| `ci_events` | Eventos do sistema CI (autoritativos, publicados pelo Argo) |
| `memory_events` | Requisições de escrita de memória |
| `system_events` | Alertas do sistema e logs de auditoria |

Comandos utilizados: `XADD`, `XREADGROUP`, `XACK`. Redis Pub/Sub não é utilizado para orquestração.

## Envelope de Evento

Todo evento utiliza este envelope durável:

```json
{
  "event_type": "string",
  "event_id": "uuid",
  "timestamp": "iso8601",
  "source": "planner|coder|tester|reviewer|scheduler|ci|system",
  "correlation_id": "uuid",
  "payload": {}
}
```

## Modelo de DAG

Cada nó de tarefa no DAG contém: `task_id`, `graph_id`, `task_type`, `dependencies`, `assigned_agent`, `status`, `guardrail_policy`, `retry_count`, `created_at`, `updated_at`.

**Status de tarefa permitidos:** `pending` → `ready` → `running` → `completed` / `failed` / `cancelled` / `blocked`

**Chaves Redis para estado do workflow:**

```
dag:{graph_id}
dag_tasks:{graph_id}
task:{task_id}
taskdeps:{task_id}
taskstatus:{task_id}
```

Transições inválidas são rejeitadas em código (ex.: `pending → completed`, dispatch de `merge_task` sem aprovação humana).

## Pipeline de Tarefas Padrão

```text
issue_created
  → plan_task      (Planner)
  → implement_task (Coder)
  → test_task      (Tester)
  → review_task    (Reviewer)
  → human_approval_gate
  → merge_task
```

Review, aprovação humana e merge são CI-gated. Eventos de CI do Argo são autoritativos.

**Fix loop em falha do CI:**

```text
ci_failed
  → fix_task   (Coder)
  → rerun_ci
  → continua apenas após ci_passed
```

## Integração com CI

O Argo CI escreve diretamente em `ci_events`. Eventos suportados: `ci_started`, `ci_failed`, `ci_passed`, `coverage_failed`, `security_failed`.

`coverage_failed` e `security_failed` emitem `system_alert` por serem falhas críticas de CI. Ordenação inválida de CI emite `system_alert` + `audit_log` sem avançar o estado.

## Tratamento de Falhas

O scheduler rastreia `retry_count`, `max_retry_limit`, registros de dead-letter e contadores Redis em `scheduler:metrics` e `scheduler:throughput`. Exceder o limite de retries para a progressão automática e requer atenção humana.

## Fronteira do Runtime

`workspace/runtime/assistant_runtime.py` inicializa o barramento de eventos Redis Streams, serviço do scheduler, serviço de runtime de memória, gateway de modelos e roteamento, e validação de guardrail em dry-run.

## Fronteira do Runtime de Memória

`workspace/memory/runtime_service.py` consome `memory_write_requested` de `memory_events`. Valida payloads, rejeita armazenamento de conversas brutas em runtime, persiste registros estruturados aceitos no Redis, e emite `audit_log`/`system_alert` em rejeições.

## Docs Relacionados

- [Fluxo de Dados e Integrações](./data-flow.md)
- [Segurança e Guardrails](./security.md)
- [Blueprint Completo de Arquitetura](../../docs/architecture.md)
