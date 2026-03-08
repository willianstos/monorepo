# Guia de Git

Last Updated: 08/03/2026

Guia operacional para branch, checkpoint, PR e merge neste workspace.

Se você quer o passo a passo mais didático para criar uma feature, commitar por fase, abrir PR e fechar merge, comece por [`docs/guide_feature_delivery.md`](./guide_feature_delivery.md).

Cadeia canônica de Git:

1. [`AGENTS.md`](../AGENTS.md)
2. [`docs/guide_git.md`](./guide_git.md)
3. [`docs/contracts/worktree-policy.md`](./contracts/worktree-policy.md)
4. [`.agent/workflows/git.md`](../.agent/workflows/git.md)
5. [`.agent/workflows/pr.md`](../.agent/workflows/pr.md)
6. [`.agent/workflows/merge-ready.md`](../.agent/workflows/merge-ready.md)
7. [`.agent/workflows/post-merge.md`](../.agent/workflows/post-merge.md)
8. [`docs/gitea-pr-validation.md`](./gitea-pr-validation.md)

## Autoridade

- **Gitea** é o host mestre e autoritativo para PR, CI e merge.
- O repositório na **Gitea** pode ficar público para leitura local sem mudar essa autoridade.
- **GitHub** é espelho subordinado somente para distribuição e backup; não governa PR, CI ou merge.
- `main` é a branch protegida e canônica.
- `git worktree` é o sandbox mutável padrão quando houver concorrência.

## Branches

- Abra branches curtas a partir da `main` atual.
- Prefixos esperados: `feature/*`, `fix/*`, `chore/*`.
- Mantenha a branch focada em uma mudança revisável.
- Use escopo único por branch (ex.: somente `.agent/workflows` para documentação de fluxo).
- Para worktree criado pelo helper do repo, o padrão é `feature/<yyyymmdd>-<slug>-<random>`.

## Worktree Padrão

- Base adotada em 08/03/2026: checkout principal estável + worktree dedicado para mutação concorrente.
- Root padrão do worktree: `../.worktrees/<repo-name>/<yyyymmdd>/<branch-name>`.
- Use WSL para criar e operar worktrees.
- Use o helper do repo:

```bash
bash bootstrap/git-worktree.sh create "08/03/2026" "agent-workflows-main"
```

- Liste worktrees:

```bash
bash bootstrap/git-worktree.sh list
```

## Fluxo Canônico

1. Atualize a `main` local e crie a branch de trabalho.
   - Se houver chance de concorrência mutável, crie primeiro um worktree dedicado.
   - Se o espelho GitHub ainda não foi registrado nesta instalação WSL, rode `bash bootstrap/github-mirror-auth.sh ensure` uma vez. O helper tenta HTTPS com `gh` e, se necessário, provisiona `pushurl` SSH com deploy key do repositório.
   - O fallback SSH usa alias fixo `github-mirror-<owner>-<repo>` e título fixo `wsl-github-mirror-<owner>-<repo>`.
   - Se `ensure` falhar no `git push --dry-run`, rode `bash bootstrap/github-mirror-auth.sh web` para reautenticação assistida por browser antes de insistir no PAT local.
2. Trabalhe e faça commits locais normais.
3. Rode `/validate` quando a mudança exigir validação local.
4. Rode `/git <dd/mm/aaaa> <branch-slug>` a partir do WSL para checkpoint, sincronização e evidência.
5. Abra o PR na Gitea contra `main`.
6. Aguarde CI verde e aprovação humana.
7. Rode `/merge-ready` como checklist final antes do clique de merge.
8. Faça o merge somente pela rota protegida da Gitea.
9. Rode `/post-merge <branch-name>` para restaurar baseline local, limpar branch e sincronizar o espelho subordinado.
   - Se precisar antecipar merge em branch de trabalho para revisão formal, use `/git --merge-main --scope ...`.

## O Que `/git` Faz

- Cria checkpoint da branch quando houver mudanças pendentes.
- Garante o bootstrap do espelho GitHub quando o remote `github` estiver configurado.
- Envia a branch ativa primeiro para `origin` como remoto mestre/autoritativo e depois tenta sincronizar o espelho `github`.
- Registra a execução em `.context/runs/git/`.
- Não cria worktree; isso é responsabilidade do helper `bootstrap/git-worktree.sh`.
- O bootstrap do espelho considera válido apenas o que passa em `git push --dry-run` no remote `github`.
- Se o fallback SSH não ficar saudável, o helper restaura o `pushurl` anterior do remote `github`.
- O modo `web` faz `gh auth login -w`, recompõe o credential helper e repete a validação do espelho.

Sintaxe e opções ficam em [`.agent/workflows/git.md`](../.agent/workflows/git.md).

## O Que `/merge-ready` Faz

- Verifica se o PR certo já existe na Gitea contra `main`.
- Confirma se os checks obrigatórios estão verdes e se a aprovação humana existe.
- Confirma se o merge vai acontecer no host mestre/autoritativo e não por atalho local.
- Não mergeia; apenas fecha o checklist final.

Sintaxe e checklist ficam em [`.agent/workflows/merge-ready.md`](../.agent/workflows/merge-ready.md).

## O Que `/post-merge` Faz

- Atualiza a baseline local com `origin/main` depois que o merge autoritativo já ocorreu.
- Sincroniza `main` para o espelho `github` só depois do refresh de `origin/main`.
- Limpa branch local/remota e prune de worktree quando aplicável.
- Não substitui o merge; só faz higiene operacional pós-merge.

Sintaxe e checklist ficam em [`.agent/workflows/post-merge.md`](../.agent/workflows/post-merge.md).

## O Que `/git` Não Faz

- Não abre PR.
- Não substitui revisão, CI ou aprovação humana.
- Não autoriza push direto para `main`.
- Não transforma GitHub em host autoritativo; mesmo com deploy key SSH funcional, a autoridade continua na Gitea.
- Não transforma `--merge-main` em bypass de proteção.
- `--merge-main` sem `--scope` é bloqueado; use `--allow-wide-merge` apenas para casos aprovados de mudança transversal.
- Não elimina a necessidade de isolamento por `worktree` quando houver mutação paralela.

## Regras de Merge

- Push direto para `main` está fora do fluxo canônico.
- Merge exige PR na Gitea, checks obrigatórios verdes e aprovação humana registrada.
- `--merge-main` continua subordinado às mesmas proteções documentadas.
- `--merge-main` exige branch limpa no momento da operação para evitar commit automático acidental.

## Modelo Mental

- O trabalho de branch termina com `/git`; a integração em `main` passa por `/pr` e `/merge-ready`.
- O trabalho mutável concorrente começa em `worktree`; o fechamento continua em `/git`, PR e higiene com `/post-merge`.
- Gitea governa merge, PR e CI como remoto mestre mesmo quando o repositório estiver público; GitHub apenas espelha como remoto subordinado.
- Nada entra em `main` sem PR, CI verde e aprovação humana.
