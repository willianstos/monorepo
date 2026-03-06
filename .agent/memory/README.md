# Agent Memory

This directory is for agent-local memory notes and lightweight distilled context.

It is not the authoritative runtime memory backend. The current runtime memory model is described in:

- `workspace/memory/manager.py`
- `workspace/config/memory.yaml`
- `workspace/runtime/assistant_runtime.py`

## Intended Contents

- distilled decisions worth reusing across sessions
- architecture notes that help future agent runs
- short operational reminders or migration notes

## Do Not Store Here

- raw chat transcripts
- copied prompt histories
- secrets, tokens, or credentials
- CI logs dumped without distillation
- large vendor documentation snapshots that belong in `.context/`

## Conventions

- prefer short Markdown notes with a date in the filename when history matters
- keep entries human-readable and safe to inspect in version control
- if a note becomes durable project knowledge, link it from `.context/docs/README.md`

This folder should stay curated and small. If it turns into a log dump, it has failed its purpose.
