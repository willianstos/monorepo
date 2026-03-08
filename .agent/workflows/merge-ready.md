# /merge-ready
---
description: Final checklist before merging a PR through the Gitea master gate.
trigger: /merge-ready
args: "[pr-url]"
runner: any
version: 1.0.0
---

## What it is

A final human-facing merge-readiness checklist.

Use it after the PR already exists in Gitea and before anyone clicks merge on the master host.

## When to use

- After `/pr` has been completed.
- When CI is green and approval is being confirmed.
- Before merging a protected branch into `main`.

## When NOT to use

- Before the branch has been published with `/git`.
- As a replacement for CI, PR review, or human approval.
- To merge locally or push directly to `main`.

## Run

```text
/merge-ready
/merge-ready <gitea-pr-url>
```

## Flow

1. **Confirm PR target**: verify the PR targets `main` on Gitea, the master authoritative host.
2. **Confirm branch state**: verify the reviewed branch is the same branch last published by `/git`.
3. **Confirm checks**: require the mandatory Gitea CI checks to be green.
4. **Confirm review**: require explicit human approval and no unresolved blocking comments.
5. **Confirm scope**: ensure no unrelated local work is being mistaken as part of the PR.
6. **Merge on Gitea**: merge only through the protected Gitea UI/API path.

## Guardrails

- `origin`/Gitea is the only merge authority.
- `github` mirror status never substitutes for Gitea review, CI, or approval.
- Do not merge from the local CLI as a convenience shortcut.
- If the branch is stale, update the PR branch first and re-run the gate.
- If any required check is missing, the PR is not merge-ready.

## Merge-Ready Checklist

- [ ] PR exists on Gitea and targets `main`.
- [ ] Branch matches the intended feature scope.
- [ ] Required Gitea checks are green.
- [ ] At least one human approval is recorded.
- [ ] No unresolved blocker comments remain.
- [ ] No extra local changes are being smuggled into the merge decision.
- [ ] Merge will happen on Gitea, not by local push.

## Mental model

`/merge-ready` does not merge. It answers whether the Gitea master gate may be used safely.
