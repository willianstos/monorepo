---
type: doc
name: tooling
description: Scripts, IDE settings, automation, and developer productivity tips
category: tooling
generated: 2026-03-05
status: active
scaffoldVersion: "2.0.0"
---

# Guia de Ferramentas e Produtividade

> Snapshot gerado. Não autoritativo.
> Veja [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md), [`../../WORKSPACE.md`](../../WORKSPACE.md) e os arquivos-fonte do repositório como fontes canônicas.

## Ferramentas Python

Toda a configuração de ferramentas está em `pyproject.toml`.

| Ferramenta | Versão | Finalidade |
|-----------|--------|-----------|
| pytest | ≥8.3.0 | Testes unitários e de integração |
| ruff | ≥0.9.0 | Linter Python rápido (line-length=100, target=py311) |
| mypy | ≥1.14.0 | Verificação estática de tipos |

### Instalação

```bash
python -m pip install -e .[dev]
```

### Comandos Comuns

```bash
# Executar todos os testes
python -m pytest

# Executar testes que correspondam a um padrão
python -m pytest -k <padrão>

# Lint
python -m ruff check workspace projects

# Verificação de tipos
python -m mypy workspace
```

## Ferramentas de Infraestrutura

### Redis via Docker Compose

O Redis é o backbone de orquestração. Uma instância de integração dedicada roda na porta 6380.

**Iniciar o Redis:**
```bash
docker compose -f docker-compose.redis.yml up -d redis-integration
```

**Parar o Redis:**
```bash
docker compose -f docker-compose.redis.yml down
```

**Inspecionar o estado do Redis diretamente:**
```bash
# Eventos de auditoria
docker exec redis-integration redis-cli XRANGE system_events - +

# Métricas do scheduler
docker exec redis-integration redis-cli HGETALL scheduler:metrics
docker exec redis-integration redis-cli HGETALL scheduler:throughput
```

## CLI de Validação Local

`bootstrap/local_validation.py` é a ferramenta principal de orquestração local. Simula o workflow completo sem um sistema CI ativo.

```bash
# Snapshot do estado atual do scheduler/Redis
REDIS_PORT=6380 python bootstrap/local_validation.py snapshot

# Iniciar um item de trabalho
REDIS_PORT=6380 python bootstrap/local_validation.py issue --graph-id <id> --objective "<desc>"

# Executar uma iteração do scheduler
REDIS_PORT=6380 python bootstrap/local_validation.py scheduler-once

# Simular resultado de tarefa
REDIS_PORT=6380 python bootstrap/local_validation.py task-result \
  --graph-id <id> --task-id <task-id> --source <agente> --event-type task_completed

# Simular eventos de CI
REDIS_PORT=6380 python bootstrap/local_validation.py ci-event \
  --event-type ci_passed --graph-id <id>

# Registrar aprovação humana
REDIS_PORT=6380 python bootstrap/local_validation.py approve \
  --graph-id <id> --approval-source human --approval-status approved --approval-actor local-operator

# Completar merge
REDIS_PORT=6380 python bootstrap/local_validation.py merge-complete --graph-id <id>

# Escrever registro de memória
REDIS_PORT=6380 python bootstrap/local_validation.py memory-write \
  --graph-id <id> --task-id <task-id> --records-json '[...]'
```

Veja o [Runbook de Validação Local](./local-validation.md) para sequências passo a passo completas.

## Scripts de Bootstrap

`bootstrap/` contém scripts idempotentes para configuração de ambiente no Windows/WSL:

- Automação de bootstrap do host e WSL
- Scripts de healthcheck para verificar o ambiente
- `local_validation.py` — a CLI principal de orquestração local

## Recomendações de IDE e Ambiente

**SO Recomendado:** WSL Ubuntu 24.04. O repositório é projetado para a experiência de workspace WSL no Windows.

**Ambiente virtual:** Crie um venv Python 3.11+. O caminho `.context/.venv/` é usado em alguns comandos de testes de integração.

**Configuração de ambiente:** Templates ficam em `env/`. Copie e preencha os arquivos `.env` conforme necessário para chaves de provedores locais e configuração do Redis.

## Dependências Principais

| Pacote | Finalidade |
|--------|-----------|
| langgraph ≥0.6.0 | Orquestração de workflow multi-agente |
| langchain ≥0.3.0 | Integração com LLM e encadeamento |
| pydantic ≥2.10.0 | Validação de dados e schemas |
| redis ≥5.2.0 | Barramento de eventos Redis Streams e persistência de estado |

## Docs Relacionados

- [Workflow de Desenvolvimento](./development-workflow.md)
- [Estratégia de Testes](./testing-strategy.md)
- [Runbook de Validação Local](./local-validation.md)
