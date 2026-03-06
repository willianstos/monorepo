# Environment

> Last Updated: 06/03/2026

This directory stores auditable environment templates for the monorepo and for the local hybrid Windows + WSL platform contract.

Current intent:

- `env/.env.example` is the canonical template for workspace defaults plus the local Gitea stack contract.
- Live secrets must stay outside the repo in the operational `.env` owned by the WSL stack.
- Placeholder markers such as `__generate_strong_secret__` must be replaced in the live `.env`, never committed as real values.

Recommended future contents:

- provider configuration templates
- per-environment policy files
- redacted examples for additional local infrastructure
