# /compact
---
description: Summarize the current repository and session state into durable local run notes.
trigger: /compact
args: ""
runner: any
version: 1.0.0
---

## What it is

A workflow for compressing active session context into local run artifacts under `.context/runs/`.

## When to use

- When the session is getting large and you want a clean continuation point.
- Before handing work to another operator window.
- After a meaningful milestone that should be resumable without replaying the full chat.

## When NOT to use

- As a substitute for repository policy or durable architectural docs.
- To save raw transcripts, secrets, or large prompt dumps.

## Run

```text
/compact
```

## Flow

1. **Inspect state**: review `git status` and the current mission context.
2. **Capture snapshot**: write `.context/runs/HAM_SNAPSHOT_LATEST.md` with the current HAM links and reuse notes.
3. **Write session summary**: write `.context/runs/ACTIVE_SESSION.md` with the main goal, resolved work, remaining work, and memory links.
4. **Prepare handoff**: return the path to the generated file and the resume prompt for the next window.

## Outputs

- `.context/runs/HAM_SNAPSHOT_LATEST.md`
- `.context/runs/ACTIVE_SESSION.md`

## Guardrails

- Do not store raw conversation logs, secrets, or prompt dumps.
- Keep summaries short, operational, and reusable.
- Treat `.context/` as state and evidence only, never as policy authority.
- Link back to authoritative docs such as [`../../AGENTS.md`](../../AGENTS.md) and [`../../CLAUDE.md`](../../CLAUDE.md) when needed.

## Mental model

`/compact` saves continuity, not authority.
