# Runbook de Validação Local

**Fonte canônica:** [docs/local-validation.md](../../docs/local-validation.md)

Este runbook cobre a validação do scheduler, Redis Streams, autoridade do CI, gate de aprovação humana e gate de merge localmente — sem construir uma plataforma de orquestração completa.

## 1. Configuração de Integração com Redis

Inicie a instância Redis dedicada usada por testes de integração e orquestração local:

```bash
docker compose -f docker-compose.redis.yml up -d redis-integration
```

Execute os testes de integração com Redis:

```bash
REDIS_INTEGRATION_PORT=6380 .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q
```

Inspecione eventos de auditoria e métricas diretamente:

```bash
docker exec redis-integration redis-cli XRANGE system_events - +
docker exec redis-integration redis-cli HGETALL scheduler:metrics
docker exec redis-integration redis-cli HGETALL scheduler:throughput
```

## 2. Snapshot do Estado Atual

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py snapshot
```

## 3. Fluxo Local Controlado (Pipeline Completo)

Valida o caminho de orquestração completo passo a passo.

**Iniciar um item de trabalho:**

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py issue \
  --graph-id demo-001 --objective "Validate scheduler hardening"
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
```

**Simular conclusões de tarefas dos agentes:**

```bash
# Planner conclui plan_task
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py task-result \
  --graph-id demo-001 --task-id demo-001:plan_task --source planner --event-type task_completed
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once

# Coder conclui implement_task
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py task-result \
  --graph-id demo-001 --task-id demo-001:implement_task --source coder --event-type task_completed
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once

# Tester conclui test_task
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py task-result \
  --graph-id demo-001 --task-id demo-001:test_task --source tester --event-type task_completed
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
```

**Simular autoridade do CI (fronteira Argo):**

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py ci-event \
  --event-type ci_passed --graph-id demo-001
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
```

**Reviewer conclui review_task:**

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py task-result \
  --graph-id demo-001 --task-id demo-001:review_task --source reviewer --event-type task_completed
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
```

**Aprovação humana e merge (não bypassável):**

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py approve \
  --graph-id demo-001 --approval-source human --approval-status approved --approval-actor local-operator
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once

REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py merge-complete \
  --graph-id demo-001
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
```

> Se `merge-complete` for publicado antes da aprovação ser registrada, o scheduler o rejeita e emite `system_alert` e `audit_log`. Isso valida a aplicação do gate de merge.

## 4. Validação do Runtime de Memória

Publique uma requisição estruturada de escrita de memória e execute o runtime de memória:

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py memory-write \
  --graph-id demo-001 --task-id demo-001:review_task \
  --records-json '[{"memory_type":"decision","topic":"Audit trail","summary":"Use audit_log on system_events.","confidence":0.9,"tags":["scheduler","audit"]}]'

REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py memory-once
```

Campos de conversa bruta são rejeitados em runtime e registrados em `system_events`.

## 5. Fronteiras da Simulação Local

| Fronteira | Simulação Local |
|-----------|----------------|
| Entrada de requisição | Comando `issue` manual ou issue do Gitea |
| Planner | Simulado via `task-result --source planner` |
| CI (Argo) | Simulado via `ci-event --event-type ci_passed/ci_failed` |
| Aprovação humana | Simulada via comando `approve` com `source=human` |
| Gitea | Fronteira de hospedagem de código — não conectado ao Redis diretamente |

## Docs Relacionados

- [Estratégia de Testes](./testing-strategy.md)
- [Guia de Ferramentas](./tooling.md)
- [Arquitetura](./architecture.md)
