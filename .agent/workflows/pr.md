# /pr
---
description: Prepare the branch for the mandatory Gitea PR path.
trigger: /pr
args: ""
runner: any
version: 1.0.0
---

## What it is

A short execution reminder for the canonical PR handoff.

## When to use

- When feature development is complete.
- Before merging any change into a protected branch.

## When NOT to use

- During active coding.
- For trivial local experiments.

## Run

```text
/pr
```

## Flow

1. **Validate**: run `/validate` when local validation is needed.
2. **Checkpoint**: run `/git` to sync the feature branch.
3. **Open PR**: create the PR in Gitea against `main`.
4. **Wait for gates**: require green CI and human approval before merge.

## Guardrails

- Follow [`../../docs/guide_git.md`](../../docs/guide_git.md) for the Git policy chain.
- Use [`../../docs/gitea-pr-validation.md`](../../docs/gitea-pr-validation.md) for branch-protection and Gitea Actions details.
- Repository-wide delivery constraints remain in [`../../AGENTS.md`](../../AGENTS.md).

## Mental model

The PR is the gated path into `main`; `/git` only gets the branch there.

## Never forget

`branch -> commit -> CI -> review -> human approval -> merge`.
