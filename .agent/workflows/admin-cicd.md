# /admin-cicd
---
description: Advanced operator workflow for handing a branch into Gitea CI/CD and closing the protected merge gate correctly.
trigger: /admin-cicd
args: "[gitea-pr-url]"
runner: any
version: 1.0.0
---

## What it is

An advanced maintainer workflow for the point where branch work is finished and the branch should move through the authoritative Gitea CI/CD gate.

It is intentionally not a blind auto-merge shortcut. In this repository, `main` still requires green CI and explicit human approval before merge.

## When to use

- After `/git` has already published the current branch.
- After `/pr` has already opened the Gitea PR.
- When a maintainer wants the shortest safe path from published branch to merge decision.

## When NOT to use

- During active coding.
- Before the branch exists on `origin`.
- As a bypass for human approval, protected branch rules, or the Gitea merge gate.
- To treat GitHub mirror status as merge authority.

## Run

```text
/admin-cicd
/admin-cicd <gitea-pr-url>
```

## Flow

1. **Confirm source branch**: verify the active feature branch is the branch last checkpointed with `/git`.
2. **Confirm PR authority**: verify the PR exists on Gitea against `main`.
3. **Hand off to CI/CD**: wait for the required Gitea checks to run and finish.
4. **Review the gate**: require green checks, explicit human approval, and no unresolved blockers.
5. **Close the merge gate**: run `/merge-ready` and merge only through the protected Gitea UI or API path.
6. **Restore baseline**: after the merge already exists on Gitea, run `/post-merge <branch-name>`.

## Guardrails

- `origin`/Gitea remains the only authoritative CI/CD and merge host.
- `github` is a subordinate mirror only.
- Current repository policy does **not** allow zero-human auto-merge into `main`.
- If the Gitea instance exposes an auto-merge capability, do not arm it for `main` unless `AGENTS.md` changes through a reviewed PR first.
- CI green alone is not enough; approval is still mandatory.

## Admin Checklist

- [ ] The branch was already published with `/git`.
- [ ] The PR exists on Gitea and targets `main`.
- [ ] Required checks are running on Gitea, not inferred from GitHub.
- [ ] Required checks are green.
- [ ] Human approval is recorded after CI passes.
- [ ] No unresolved blocker comments remain.
- [ ] Merge will happen on Gitea, not by local push.
- [ ] `/post-merge` is queued for cleanup after the authoritative merge.

## Mental model

`/admin-cicd` is the advanced operator lane into CI/CD. It accelerates the handoff, not the authority model.
