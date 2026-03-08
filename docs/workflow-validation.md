# Validação de Workflows

Guia humano de validação da camada de workflows em [`.agent/workflows/`](../.agent/workflows/README.md). Não substitui `AGENTS.md`, os workflows, nem a camada de estado em `.context/`.

## O Que Validar

- Estrutura e consistência de `/git`, `/pr`, `/merge-ready`, `/post-merge`, `/validate`, `/super-review`, `/release-note` e `/workflow-map`.
- Alinhamento entre texto dos workflows e os comandos/documentos referenciados.
- Ausência de contradição com `AGENTS.md`, `GUARDRAILS.md` e `docs/*`.

## Execução

```bash
python -m pytest workspace/tests/
```

## Classificação

| Workflow | Tipo de validação |
|----------|-------------------|
| `/git` | Simulação executável via `--dry-run` |
| `/validate` | Consistência de comandos e contrato |
| `/pr` | Consistência de referências e gate |
| `/merge-ready` | Checklist final e ausência de bypass local |
| `/post-merge` | Limpeza pós-merge e precedência correta de remoto |
| `/super-review` | Guardrails, escopo de auditoria e não substituição do CI remoto |
| `/release-note` | Contrato e guardrails |
| `/workflow-map` | Contrato e ausência de contradição |

## Comandos Alinhados

- `python -m ruff check workspace projects`
- `python -m mypy workspace`
- `python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q`
- `python -m pytest workspace/scheduler/test_redis_integration.py -q`
- `python -m compileall bootstrap workspace`

## Verificações Humanas

- PR real na Gitea.
- Aprovação humana.
- Disponibilidade de merge após CI verde.

A validação de workflows verifica a camada de execução. A autoridade final é `AGENTS.md` + CI + revisão + aprovação humana.
