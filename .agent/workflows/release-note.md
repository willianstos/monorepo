# /release-note
---
description: Create a concise release note or closeout summary from current repo changes.
trigger: /release-note
args: ""
runner: any
version: 1.0.0
---

## What it is

A change-summary workflow for reviewer-facing and operator-facing writeups.

## When to use

- When closing an epic or completing a significant feature.
- Before merging a PR to provide context to reviewers.

## When NOT to use

- For minor typo fixes.
- To invent roadmap claims not present in the code or docs.

## Run

```text
/release-note
```

## Flow

1. **Diff analysis**: inspect committed changes against `main`.
2. **Context retrieval**: read the relevant task, PR, or epic material.
3. **Synthesis**: generate a short summary of what changed, why, and impact.

## Outputs

- Markdown ready for a PR description, closeout note, or changelog entry.

## Guardrails

- Do not include sensitive infrastructure details.
- Base repository references on [`../../AGENTS.md`](../../AGENTS.md), [`../../WORKSPACE.md`](../../WORKSPACE.md), and the current diff.
- Do not invent roadmap, architecture, or policy claims that are not present in the repository.
