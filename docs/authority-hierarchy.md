# Authority Hierarchy

Reference guide for the frozen authority hierarchy. [`AGENTS.md`](../AGENTS.md) remains the single global contract.

## Layers

1. **`AGENTS.md`** — global repository contract and instruction root.
2. **`.agent/rules/`** — shared operational rules.
3. **`.agent/workflows/`** — execution playbooks.
4. **`.agent/skills/`** — capability assets.
5. **`.claude/`** — Claude-specific extensions.
6. **`.context/`** — state, evidence, and generated artifacts only.
7. **Legacy/tool-specific files** — compatibility pointers only.

## Prohibited Actions

- Do not create a second global contract.
- Do not place operational rules outside `.agent/rules/`.
- Do not place workflow execution logic outside `.agent/workflows/`.
- Do not treat `.context/` as policy authority.
- Do not let IDE or tool-specific instructions outrank canonical files.
- Do not leave legacy files sounding authoritative.

## Change Gate

Any hierarchy change is a governance change. It requires explicit human review in a PR, even for documentation-only diffs.
