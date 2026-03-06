---
type: doc
name: testing-strategy
description: Test frameworks, patterns, coverage requirements, and quality gates
category: testing
generated: 2026-03-05
status: active
scaffoldVersion: "2.0.0"
---

# Estratégia de Testes

## Framework de Testes

Este projeto utiliza **pytest** (≥8.3.0) com caminhos de teste configurados em `pyproject.toml` cobrindo `workspace/` e `projects/`.

## Tipos de Testes

### Testes Unitários

Executar todos os testes unitários:

```bash
python -m pytest
```

Executar testes que correspondam a um padrão:

```bash
python -m pytest -k <padrão>
```

**Testes unitários do scheduler** (`workspace/scheduler/test_orchestration.py`):

- Testa construção de DAG a partir de eventos `issue_created`
- Testa criação de fix-loop em falha do CI
- Testa validação de transições de tarefas
- Testa aplicação de guardrails
- Testa idempotência de eventos duplicados
- Testa tratamento de dead-letter

### Testes de Integração com Redis

Requer uma instância Redis em execução na porta 6380.

**Iniciar o Redis:**

```bash
docker compose -f docker-compose.redis.yml up -d redis-integration
```

**Executar testes de integração:**

```bash
REDIS_INTEGRATION_PORT=6380 python -m pytest workspace/scheduler/test_redis_integration.py -q
```

Esses testes validam o loop completo do scheduler contra Redis Streams real, incluindo criação de consumer groups, publicação de eventos e persistência de estado.

## Análise Estática

### Lint

```bash
python -m ruff check workspace projects
```

Configuração: line-length=100, target-version=py311 (ver `pyproject.toml`).

### Verificação de Tipos

```bash
python -m mypy workspace
```

## Gates de Qualidade do CI

O CI é autoritativo. Antes que uma tarefa possa avançar além de `test_task` ou fazer merge para `main`, o CI deve passar. O scheduler aplica isso em código:

- Bloqueando `review_task`, `human_approval_gate` e `merge_task` até que `ci_passed` seja recebido em `ci_events`
- Tratando `coverage_failed` e `security_failed` como falhas críticas (emite `system_alert`)
- Criando um fix loop em `ci_failed` e bloqueando tarefas downstream até um `ci_passed` posterior

## Expectativas de Validação por Tipo de Mudança

| Tipo de Mudança | Verificações Necessárias |
|----------------|------------------------|
| Código Python | `pytest`, `ruff check`, `mypy` |
| Scheduler/event bus | `pytest` + testes de integração Redis |
| Apenas documentação | Declare que a validação foi pulada ou limitada |
| Política/guardrails | `pytest` para confirmar que os testes do enforcer passam |

## Docs Relacionados

- [Workflow de Desenvolvimento](./development-workflow.md)
- [Runbook de Validação Local](./local-validation.md)
- [Guia de Ferramentas](./tooling.md)
