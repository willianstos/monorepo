# Guia de Git

Guia operacional para branch, checkpoint, PR e merge neste workspace.

Cadeia canônica de Git:

1. [`AGENTS.md`](../AGENTS.md)
2. [`docs/guide_git.md`](./guide_git.md)
3. [`.agent/workflows/git.md`](../.agent/workflows/git.md)
4. [`docs/gitea-pr-validation.md`](./gitea-pr-validation.md)

## Autoridade

- **Gitea** é o host autoritativo para PR, CI e merge.
- **GitHub** é espelho somente.
- `main` é a branch protegida e canônica.

## Branches

- Abra branches curtas a partir da `main` atual.
- Prefixos esperados: `feature/*`, `fix/*`, `chore/*`.
- Mantenha a branch focada em uma mudança revisável.
- Use escopo único por branch (ex.: somente `.agent/workflows` para documentação de fluxo).

## Fluxo Canônico

1. Atualize a `main` local e crie a branch de trabalho.
2. Trabalhe e faça commits locais normais.
3. Rode `/validate` quando a mudança exigir validação local.
4. Rode `/git <dd/mm/aaaa> <branch-slug>` a partir do WSL para checkpoint, sincronização e evidência.
5. Abra o PR na Gitea contra `main`.
6. Aguarde CI verde e aprovação humana.
7. Faça o merge somente pela rota protegida da Gitea.
   - Se precisar antecipar merge em branch de trabalho para revisão formal, use `/git --merge-main --scope ...`.

## O Que `/git` Faz

- Cria checkpoint da branch quando houver mudanças pendentes.
- Envia a branch ativa para `origin` e `github`.
- Registra a execução em `.context/runs/git/`.

Sintaxe e opções ficam em [`.agent/workflows/git.md`](../.agent/workflows/git.md).

## O Que `/git` Não Faz

- Não abre PR.
- Não substitui revisão, CI ou aprovação humana.
- Não autoriza push direto para `main`.
- Não transforma `--merge-main` em bypass de proteção.
- `--merge-main` sem `--scope` é bloqueado; use `--allow-wide-merge` apenas para casos aprovados de mudança transversal.

## Regras de Merge

- Push direto para `main` está fora do fluxo canônico.
- Merge exige PR na Gitea, checks obrigatórios verdes e aprovação humana registrada.
- `--merge-main` continua subordinado às mesmas proteções documentadas.
- `--merge-main` exige branch limpa no momento da operação para evitar commit automático acidental.

## Modelo Mental

- O trabalho de branch termina com `/git`; a integração em `main` termina com PR.
- Gitea governa merge; GitHub apenas espelha.
- Nada entra em `main` sem PR, CI verde e aprovação humana.
