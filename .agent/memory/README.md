# Agent Memory

> Last Updated: 2026-03-06

This directory is for shared, tool-agnostic memory notes and lightweight distilled context. It is not the authoritative runtime memory backend, and it is not the same thing as `.claude/memory/`.

## Intended Contents

- distilled decisions worth reusing across sessions
- architecture notes that help future agent runs
- short operator reminders or migration notes

## Do Not Store Here

- raw chat transcripts
- copied prompt histories
- secrets, tokens, or credentials
- raw CI logs or terminal dumps
- large vendor documentation snapshots that belong in `.context/`

## Memory Tips

- Save only stable facts, constraints, and short lessons.
- Distill before saving. Deduplicate when updating.
- Flush or rewrite notes when the original task is done and only the durable lesson matters.
- Keep entries small enough to scan quickly.

## Conventions

- Prefer short Markdown notes with a date in the filename when history matters.
- Keep entries human-readable and safe to inspect in version control.
- If a note becomes canonical durable project knowledge, move or mirror it into `.claude/memory/` or a checked-in doc.
