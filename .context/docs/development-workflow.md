---
type: doc
name: development-workflow
description: Day-to-day engineering processes, branching, and contribution guidelines
category: workflow
generated: 2026-03-05
status: active
scaffoldVersion: "2.0.0"
---

# Workflow de Desenvolvimento

## Configuração do Ambiente

1. Crie e ative um ambiente virtual Python 3.11+.
2. Instale o pacote e as ferramentas de desenvolvimento:
   ```bash
   python -m pip install -e .[dev]
   ```
3. Mantenha notas geradas, scaffolds e artefatos de execução dentro de `.context/`.

**SO Recomendado:** WSL Ubuntu 24.04 no Windows. O repositório é projetado para a experiência de workspace WSL.

## Comandos Comuns

| Comando | Finalidade |
|---------|-----------|
| `python -m pytest` | Executar todos os testes unitários |
| `python -m pytest -k <padrão>` | Executar testes que correspondam a um padrão |
| `REDIS_INTEGRATION_PORT=6380 python -m pytest workspace/scheduler/test_redis_integration.py -q` | Testes de integração com Redis |
| `python -m ruff check workspace projects` | Lint do código Python |
| `python -m mypy workspace` | Verificação de tipos do código Python |
| `REDIS_PORT=6380 python bootstrap/local_validation.py snapshot` | Snapshot do estado do scheduler/Redis |

## Fronteiras de Mudança

| Diretório | Quando Editar |
|-----------|--------------|
| `.agent/` | Curadoria de skills locais, catálogos de skills vendorizados, notas de workflow ou ativos de memória locais dos agentes. Trate `.agent/catalogs/` como conteúdo de terceiros, a menos que a mudança seja intencional. |
| `workspace/` | Código-fonte Python, contratos e comportamento de runtime do blueprint |
| `guardrails/` + `GUARDRAILS.md` | Mudanças de política — edite ambos juntos |
| `docs/`, `README.md`, `WORKSPACE.md` | Mudanças na arquitetura ou regras operacionais |
| `bootstrap/` | Bootstrap Windows/WSL, healthcheck e automação do ambiente de desenvolvedor |
| `.context/` | Adição de nova documentação reutilizável ou playbooks de agentes; atualize os índices ao fazer isso |
| `projects/` | Seeds de projetos-alvo e notas específicas de projetos apenas |

## Expectativas de Documentação

- Mantenha os docs de nível superior alinhados com mudanças na estrutura do repositório.
- Não descreva o repositório como "apenas placeholders" — os contratos scheduler/event-bus/runtime estão implementados.
- Vincule novos guias de longa duração a partir de `.context/docs/README.md`.
- Vincule novas instruções reutilizáveis de agentes a partir de `.context/agents/README.md`.
- Inclua payloads de exemplo ou markdown gerado quando esquemas ou scaffolds mudarem materialmente.

## Expectativas de Validação

- Execute `python -m pytest` para qualquer mudança de código.
- Inicie o Redis com `docker compose -f docker-compose.redis.yml up -d redis-integration` antes de executar testes de integração.
- Execute `ruff check` e `mypy` para mudanças estruturais em Python.
- Para mudanças apenas de documentação, declare que a validação foi pulada ou limitada.

## Política de Merge

Nenhuma tarefa pode fazer merge para `main` sem:

1. CI passando (com autoridade do Argo)
2. Aprovação humana registrada

O scheduler aplica isso em código — rejeita o dispatch de merge sem aprovação registrada, emitindo `system_alert` e `audit_log`.

## Docs Relacionados

- [Estratégia de Testes](./testing-strategy.md)
- [Guia de Ferramentas](./tooling.md)
- [Runbook de Validação Local](./local-validation.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
