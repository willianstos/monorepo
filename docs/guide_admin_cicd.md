# Guia Avancado: Operador de CI/CD e Merge

Last Updated: 08/03/2026

Guia para mantenedor, tech lead ou admin que quer pegar uma branch pronta, mandar para o gate remoto e fechar o merge com o menor atrito possivel sem quebrar a governanca do repositorio.

Este guia nao muda a autoridade do repositorio:

- `origin`/Gitea continua sendo o host mestre para PR, CI e merge.
- `github` continua sendo espelho subordinado.
- `main` continua exigindo CI verde e aprovacao humana registrada.

Se voce quer o fluxo de dev do dia a dia, use primeiro [`docs/guide_feature_delivery.md`](./guide_feature_delivery.md). Este aqui e o guia da reta final para operador.

## O Que Este Guia Resolve

Use este guia quando:

- a branch ja foi implementada e comitada
- a branch ja foi publicada com `/git`
- o PR ja existe ou sera aberto agora
- voce quer empurrar a mudanca ate o gate de CI/CD e decidir o merge no momento certo

## O Que Ele Nao Autoriza

Este guia nao autoriza:

- push direto em `main`
- merge local como atalho
- tratar GitHub como host autoritativo
- auto-merge cego em `main`

No contrato atual do repositorio, `main` segue esta cadeia:

```text
branch -> commit -> CI -> review -> human approval -> merge
```

## Fluxo Rapido do Operador

1. Confirmar a branch certa.
2. Garantir que a branch foi publicada com `/git`.
3. Abrir ou revisar o PR na Gitea.
4. Entregar a branch para o gate de CI/CD na Gitea.
5. Esperar checks obrigatorios verdes.
6. Registrar aprovacao humana.
7. Rodar `/merge-ready`.
8. Fazer o merge na Gitea.
9. Fechar com `/post-merge`.

## Passo 1: Confirmar o Estado da Branch

Antes de olhar para CI/CD, confirme:

- branch correta
- escopo correto
- nenhum arquivo paralelo fora do PR
- ultimo `/git` ja executado

Checklist pratico:

- a branch local e a mesma branch do PR
- o ultimo push foi para `origin`
- o diff do PR bate com o objetivo da entrega

## Passo 2: Publicar do Jeito Certo

Se ainda faltou publicar:

```text
/git 08/03/2026 <branch-slug>
```

Isso faz:

- checkpoint da branch
- push primeiro para `origin`
- sync melhor-esforco para `github`
- evidencia em `.context/runs/git/`

## Passo 3: Abrir ou Revisar o PR

Se o PR ainda nao existe:

```text
/pr
```

Na Gitea, confirme:

- base `main`
- branch de origem correta
- descricao clara
- sem arquivos estranhos no diff

## Passo 4: Mandar Para o Gate de CI/CD

Aqui entra o fluxo avancado:

```text
/admin-cicd
```

ou:

```text
/admin-cicd <url-do-pr-na-gitea>
```

O objetivo aqui nao e "merge automatico a qualquer custo". O objetivo e:

- garantir que o gate remoto correto foi acionado
- olhar os checks obrigatorios certos
- reduzir erro operacional antes do merge

## Passo 5: Esperar os Checks Certos

O operador deve olhar a Gitea, nao o GitHub.

Checks obrigatorios esperados neste repositorio:

- `Lint (ruff)`
- `Type Check (mypy)`
- `Unit Tests (pytest)`
- `Integration Tests (Redis)`

Se qualquer um estiver faltando, falhando ou preso, o PR ainda nao esta pronto.

## Passo 6: Aprovar do Jeito Certo

No contrato atual, aprovacao humana continua obrigatoria.

A leitura correta e esta:

- CI verde sozinho nao libera merge
- review sem CI verde nao libera merge
- os dois juntos liberam o uso do gate final

Se a Gitea expuser opcao de auto-merge, nao use isso para `main` neste repo sem antes mudar `AGENTS.md` em um PR aprovado. A politica raiz ainda exige aprovacao humana apos o CI passar.

## Passo 7: Fechar o Gate Final

Antes do clique de merge:

```text
/merge-ready
```

Se tudo estiver verde:

- checks obrigatorios verdes
- aprovacao humana registrada
- sem comentarios bloqueadores
- PR certo contra `main`

entao o merge pode acontecer na Gitea.

## Passo 8: Fazer o Merge

Merge profissional aqui significa:

- merge na Gitea
- nunca `git push origin main`
- nunca merge local como bypass

## Passo 9: Fazer a Higiene Pos-Merge

Depois que o merge ja aconteceu na Gitea:

```text
/post-merge <branch-name>
```

Isso restaura:

- `main` local sincronizada com `origin/main`
- espelho `github` atualizado a partir do estado autoritativo
- branch removida quando apropriado
- worktree limpo

## Exemplo Completo

```text
/git 08/03/2026 scheduler-ci-gate
/pr
/admin-cicd
/merge-ready
```

Depois do merge na Gitea:

```text
/post-merge feature/20260308-scheduler-ci-gate-abc123
```

## Se Voce Realmente Quer Auto-Merge

Hoje, a resposta correta e: nao em `main`, nao com a politica atual.

Para liberar isso de verdade, seria necessario:

1. mudar `AGENTS.md` por PR revisado
2. revisar `docs/gitea-pr-validation.md`
3. ajustar os workflows `/pr`, `/admin-cicd`, `/merge-ready` e `/post-merge`
4. validar impacto em branch protection, CI e auditoria

Enquanto isso nao acontecer, o fluxo profissional continua sendo:

```text
branch -> commit -> CI -> review -> human approval -> merge
```

## Leitura Complementar

- [Guia de Git](./guide_git.md)
- [Guia de Feature](./guide_feature_delivery.md)
- [Gitea PR Validation](./gitea-pr-validation.md)
- [Workflow Playbooks](../.agent/workflows/README.md)
