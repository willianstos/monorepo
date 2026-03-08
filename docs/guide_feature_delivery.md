# Guia de Feature: Do Commit ao Merge

Last Updated: 08/03/2026

Guia prático para um dev pegar uma feature, trabalhar em fases, abrir PR e fechar o merge do jeito certo neste repositório.

Se voce atua como maintainer/admin na reta final do PR, complemente este guia com [`docs/guide_admin_cicd.md`](./guide_admin_cicd.md).

## Regra de Ouro

- `origin`/Gitea é o remoto mestre e autoritativo.
- `github` é espelho subordinado.
- O merge em `main` acontece na Gitea, nunca por push local.

## Fluxo Rápido

1. Criar branch de trabalho.
2. Implementar a feature em fases pequenas.
3. Fazer commits por fase lógica.
4. Rodar `/validate`.
5. Rodar `/git`.
6. Abrir PR com `/pr`.
7. Se voce for o operador do gate remoto, usar `/admin-cicd`.
8. Conferir `/merge-ready`.
9. Fazer o merge na Gitea.
10. Fechar com `/post-merge`.

## Fase 0: Entender a Feature

Antes de escrever código:

- confirme o objetivo da feature
- confirme o critério de aceite
- confirme o que está fora do escopo
- confirme se a mudança é pequena o bastante para um PR revisável

Perguntas boas:

- O usuário final vai perceber qual mudança?
- Como eu provo que ficou funcionando?
- Isso mexe em implementação, teste, documentação ou nos três?
- Dá para entregar em uma branch única sem misturar assuntos?

## Fase 1: Criar o Espaço de Trabalho

Se a mudança for simples e ninguém mais estiver mexendo no checkout atual, trabalhe no checkout normal.

Se houver chance de concorrência mutável, crie um `worktree`.

Exemplo:

```bash
bash bootstrap/git-worktree.sh create "08/03/2026" "user-profile-form"
```

Se já estiver no worktree certo, confirme a branch:

```bash
git branch --show-current
```

O padrão esperado é algo como:

```text
feature/20260308-user-profile-form-abc123
```

## Fase 2: Implementar em Fases Pequenas

Não trate a feature como um bloco único. Quebre em fases.

Exemplo de fases:

1. Estrutura inicial
2. Implementação principal
3. Validação e ajustes
4. Documentação ou acabamento

### Exemplo real de divisão

Feature: adicionar formulário de perfil.

Fase 1:

- criar rota, componente base e estados mínimos

Commit sugerido:

```text
feat: scaffold user profile form
```

Fase 2:

- salvar dados
- validar campos
- tratar erro

Commit sugerido:

```text
feat: implement user profile submission
```

Fase 3:

- ajustar testes
- corrigir bordas
- alinhar logs e mensagens

Commit sugerido:

```text
test: cover user profile validation flow
```

ou

```text
fix: handle invalid profile payloads
```

Fase 4:

- atualizar documentação se necessário

Commit sugerido:

```text
docs: document user profile flow
```

## Como Fazer Bons Commits

Um commit bom:

- representa uma fase lógica
- tem mensagem clara
- não mistura refactor aleatório com feature principal
- deixa fácil revisar e reverter

Boas mensagens:

```text
feat: add user profile form shell
feat: implement profile update service
fix: prevent empty profile submissions
test: cover profile update failures
docs: document profile update workflow
```

Mensagens ruins:

```text
update
fix stuff
wip
changes
final
```

## Fase 3: Validar Antes de Publicar

Antes de empurrar a branch:

```text
/validate
```

Ou rode os comandos equivalentes se precisar:

```bash
python -m ruff check workspace projects
python -m mypy workspace
python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q
python -m compileall bootstrap workspace
```

Se a mudança exigir integração Redis, rode a validação completa.

## Fase 4: Publicar a Branch

Quando a fase de implementação estiver pronta para revisão:

```text
/git 08/03/2026 user-profile-form
```

O que isso faz:

- deixa evidência da execução
- publica primeiro em `origin`
- tenta sincronizar depois no `github`

Se o espelho GitHub ainda não estiver autenticado neste WSL:

```bash
bash bootstrap/github-mirror-auth.sh ensure
```

Se o bootstrap por token falhar:

```bash
bash bootstrap/github-mirror-auth.sh web
```

## Fase 5: Encaminhar Para PR

Com a branch já publicada:

```text
/pr
```

Na prática isso significa:

1. abrir o PR na Gitea contra `main`
2. revisar o título e a descrição
3. garantir que o PR tem escopo único
4. esperar os checks obrigatórios

O PR certo:

- tem tema único
- explica o que mudou
- explica como validar
- não carrega mudanças paralelas fora do escopo

## Fase 6: Conferir Se Está Pronto Para Merge

Antes de clicar merge:

```text
/merge-ready
```

Checklist mínimo:

- PR correto contra `main`
- checks verdes na Gitea
- aprovação humana registrada
- sem comentários bloqueadores abertos
- sem dúvida sobre o escopo da branch

Importante:

- GitHub não aprova merge aqui
- o merge autoritativo é na Gitea

## Fase 7: Fazer o Merge

Se o PR foi aprovado:

- faça o merge na Gitea
- não faça `git push origin main`
- não use merge local como atalho

O merge profissional neste repositório é:

```text
feature branch -> PR na Gitea -> CI verde -> aprovação humana -> merge na Gitea
```

## Fase 8: Limpar Depois do Merge

Depois que o merge já aconteceu na Gitea:

```text
/post-merge feature/20260308-user-profile-form-abc123
```

Isso serve para:

- atualizar `main` local a partir de `origin/main`
- sincronizar `main` para o espelho `github`
- deletar a branch local e remota
- limpar worktrees quando aplicável

## Exemplo Completo

```bash
# 1. criar worktree
bash bootstrap/git-worktree.sh create "08/03/2026" "user-profile-form"

# 2. trabalhar em fases e commitar
git add .
git commit -m "feat: scaffold user profile form"

git add .
git commit -m "feat: implement profile update service"

git add .
git commit -m "test: cover profile update validation"
```

```text
/validate
/git 08/03/2026 user-profile-form
/pr
/merge-ready
```

Depois do merge na Gitea:

```text
/post-merge feature/20260308-user-profile-form-abc123
```

## Erros Comuns

- Trabalhar direto em `main`
- Misturar várias features na mesma branch
- Abrir PR sem rodar validação
- Tratar GitHub como gate de merge
- Fazer merge local e empurrar `main`
- Esquecer de limpar branch e worktree depois do merge

## Leitura Complementar

- [Guia de Git](./guide_git.md)
- [Gitea PR Validation](./gitea-pr-validation.md)
- [Workflow Playbooks](../.agent/workflows/README.md)
- [Contributing](../CONTRIBUTING.md)
