---
type: doc
name: glossary
description: Project terminology, type definitions, domain entities, and business rules
category: glossary
generated: 2026-03-05
status: active
scaffoldVersion: "2.0.0"
---

# Glossário e Conceitos do Domínio

> Snapshot gerado. Não autoritativo.
> Veja [`../../AGENTS.md`](../../AGENTS.md) e os docs canônicos em [`../../docs/`](../../docs/) para decisões de política ou arquitetura.

## Infraestrutura Principal

**Scheduler**
O serviço central de orquestração (`workspace/scheduler/service.py`). Stateless por contrato — reconstrói todo o estado do workflow a partir do Redis a cada evento. Possui o ciclo de vida do DAG, dispatch de tarefas, aplicação de guardrails e logging de auditoria.

**Redis Streams**
O único barramento de orquestração do sistema. Agentes publicam e consomem eventos exclusivamente via Redis Streams. Chamadas diretas entre agentes não são permitidas. Utiliza `XADD`, `XREADGROUP` e `XACK`.

**Consumer Group**
Mecanismo do Redis Streams que permite múltiplos leitores compartilharem o trabalho sem entrega duplicada. O scheduler usa consumer groups para ler de `agent_results`, `ci_events` e `system_events`.

**DAG (Grafo Acíclico Dirigido)**
O grafo de execução de tarefas para um item de trabalho. Construído pelo scheduler a partir de um evento `issue_created` ou `task_graph_created`. Persistido no Redis. Nós são tarefas com dependências; arestas representam restrições de sequenciamento.

**Envelope de Evento**
O wrapper padrão para todos os eventos do sistema:
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

**correlation_id**
Um UUID que vincula todos os eventos pertencentes ao mesmo item de trabalho ou grafo. Usado para construção de trilha de auditoria e rastreamento de eventos.

## Agentes

**Planner**
O agente que interpreta requisições e prepara insumos de planejamento. Produz eventos `task_graph_created`. Não escreve código de implementação.

**Coder**
O agente que escreve apenas código de implementação. Não pode modificar testes ou configurações de CI.

**Tester**
O agente que possui testes e fixtures apenas. Não pode enfraquecer testes para forçar CI verde.

**Reviewer**
O agente que valida qualidade, consistência e conformidade com guardrails. Pode bloquear a progressão do grafo.

## Conceitos do Workflow

**issue_created**
O evento que dispara um novo item de trabalho. O scheduler constrói um DAG a partir deste evento e despacha `plan_task` para o Planner.

**task_graph_created**
Um ponto de entrada alternativo quando um agente de planejamento já produziu uma estrutura de grafo de tarefas.

**fix_task**
Uma tarefa adicionada ao DAG quando o CI falha. Atribuída ao Coder. Tarefas downstream ficam bloqueadas até que um `ci_passed` subsequente seja recebido.

**fix loop**
A sequência criada em falha do CI: `fix_task → rerun_ci`, com todas as tarefas downstream bloqueadas até o CI passar novamente.

**dead-letter**
O estado que um grafo de tarefas entra quando os limites de retry são excedidos. Requer intervenção humana — o scheduler para a progressão automática e emite um `system_alert`.

**human_approval_gate**
Uma tarefa protegida que só pode ser completada por uma fonte confiável. O scheduler bloqueia o dispatch de `merge_task` até que este gate seja registrado como completo com metadados de aprovação válidos.

**merge_task**
A tarefa final no pipeline padrão. Protegida — só pode ser despachada após `human_approval_gate` completar e o CI ter passado.

## Tipos de Eventos

| Evento | Publicado Por | Descrição |
|--------|--------------|-----------|
| `issue_created` | Externo / Planner | Dispara criação de DAG |
| `task_graph_created` | Planner | Entrada alternativa de DAG |
| `task_created` | Scheduler | Nova tarefa adicionada ao DAG |
| `task_started` | Agente | Agente iniciou o trabalho |
| `task_completed` | Agente | Agente reporta sucesso |
| `task_failed` | Agente | Agente reporta falha |
| `code_generated` | Coder | Artefato de código produzido |
| `tests_requested` | Coder/Scheduler | Execução de testes solicitada |
| `review_requested` | Scheduler | Gate de revisão acionado |
| `ci_started` | CI (Argo) | Pipeline de CI iniciado |
| `ci_failed` | CI (Argo) | Pipeline de CI falhou |
| `ci_passed` | CI (Argo) | Pipeline de CI passou |
| `coverage_failed` | CI (Argo) | Gate de cobertura falhou |
| `security_failed` | CI (Argo) | Gate de segurança falhou |
| `human_approval_required` | Scheduler | Humano deve aprovar |
| `merge_requested` | Scheduler | Gate de merge acionado |
| `system_alert` | Scheduler/Runtime | Alerta de falha crítica |
| `memory_write_requested` | Agente/Runtime | Requisição de escrita de memória |
| `audit_log` | Scheduler/Runtime | Registro de auditoria de decisão |

## Conceitos de Segurança

**Guardrail**
Uma regra de política aplicada que governa o que agentes e o scheduler podem fazer. Implementada em código (`workspace/scheduler/guardrail_enforcer.py`), não apenas em documentação.

**Fonte confiável**
Para tarefas de sistema protegidas (`human_approval_gate`, `merge_task`, `rerun_ci`), apenas eventos de fontes confiáveis designadas são aceitos. Outros são rejeitados e registrados em `audit_log`.

**Autoridade do CI**
O CI (Argo) é a fonte da verdade para validade do código. O scheduler não infere aprovação/falha da saída dos agentes — reage a eventos autoritativos de CI em `ci_events`.

**audit_log**
Um evento estruturado emitido em `system_events` para cada decisão de orquestração aceita ou rejeitada. Forma a base para análise de incidentes.

**system_alert**
Um evento emitido em `system_events` para falhas críticas: esgotamento de retries, ordenação inválida de CI, falhas de cobertura/segurança, violações do gate de merge.

## Conceitos de Memória

**MemoryRecord**
O formato estruturado obrigatório para escritas de memória. Logs de conversas brutas são rejeitados no caminho de escrita do runtime.

**memory_write_requested**
O evento publicado em `memory_events` para solicitar uma escrita de memória. Validado pelo serviço de runtime de memória antes da persistência.

**Memória de Trabalho**
Memória de curto prazo no Redis para a tarefa ou sessão atual.

**Memória de Longo Prazo**
Atualmente no Redis (sink de runtime). Destinada a evoluir para uma camada de armazenamento durável.
