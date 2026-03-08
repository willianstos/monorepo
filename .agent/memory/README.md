# Shared Agent Memory

Shared, tool-agnostic memory notes and distilled context. Not the authoritative runtime memory backend. Not `.claude/memory/`.

## Store Here

- Distilled decisions worth reusing across sessions.
- Architecture notes that help future agent runs.
- Short operator reminders or migration notes.

## Do Not Store Here

- Raw chat transcripts, prompt histories, or terminal dumps.
- Secrets, tokens, or credentials.
- Large vendor documentation (belongs in `.context/`).

## Conventions

- Save only stable facts, constraints, and short lessons.
- Distill before saving. Deduplicate when updating.
- Keep entries small enough to scan quickly.
- If a note becomes canonical project knowledge, move it to `.claude/memory/` or a checked-in doc.
