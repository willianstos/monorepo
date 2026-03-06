You are working inside 01-monorepo / 01-monolito.

This repository is a LOCAL-FIRST AI Coding Assistant workspace.
Do not redesign the architecture.
Do not add new primary agents.
Do not weaken guardrails.
Do not introduce direct agent-to-agent calls.
Do not change the fixed assistant-style / CI-authoritative / human-approval-governed design.

Primary execution agents remain:
- planner
- coder
- tester
- reviewer

Fixed architecture decisions:
- scheduler is a separate service
- Redis Streams is the only event/task bus
- DAG state persists in Redis
- agents communicate only through events
- CI is authoritative
- merge to main always requires human approval
- this is a local-first assistant workspace, not a fully autonomous engineer

We are now implementing the FINAL professional Gitea local PR validation standard for this repository.

==================================================
GOAL
==================================================

Implement a production-grade local Gitea PR validation setup for 01-monorepo using:

- Gitea Actions
- act_runner
- protected-branch-compatible validation jobs
- PR status checks
- local-first reproducibility
- no bypass of CI or human approval

This must align with current Gitea best practices:
- workflows in `.gitea/workflows/`
- act_runner intended for Docker-based execution
- runner isolation from the Gitea server when practical
- branch protection with required checks and approvals

Do not implement cloud-only assumptions.
Do not assume GitHub.
Do not assume Gemini.
This repository standard is for Gitea local first.

==================================================
REPOSITORY CONTEXT TO PRESERVE
==================================================

This repo already has:
- scheduler guardrails
- trusted-source enforcement
- memory enforcement
- audit_log events
- local validation tooling
- release-candidate local controlled flow
- Codex + Claude instruction layers
- Ollama qwen3.5:9b helper-only routing

The PR validation layer must fit this existing system and not create parallel logic.

==================================================
DELIVERABLES
==================================================

Implement the complete local Gitea PR validation standard with the following deliverables.

1. Gitea workflow files
Create or update `.gitea/workflows/` with a clean, maintainable PR validation structure.

Required workflows:
- pr-validation.yml

If useful, split internally into jobs rather than multiple workflow files, unless multiple files clearly improve clarity.

2. Validation jobs
The PR workflow must include these required jobs:

- lint
- types
- tests-unit
- tests-integration-redis

The jobs should execute the repository's real validation commands where available.

Expected command classes include:
- ruff check
- mypy workspace
- pytest for scheduler/tool tests
- pytest for Redis integration tests
- any compile/smoke step already used as part of the local RC flow if it materially improves confidence

Do not include meaningless jobs.
Do not include placeholder jobs.

3. Conditional Redis integration job
The Redis integration job must be reproducible locally.
Implement it so that:
- it can run using Docker service/container support if suitable
- or using a clearly documented local Redis path if Docker job services are unreliable in this Gitea environment

Prefer a robust implementation over a fancy one.
Document the chosen path clearly.

4. Local runner operator docs
Create or update operator-facing docs for:
- enabling Gitea Actions
- registering act_runner
- why Docker mode is preferred
- why runner should not rely on loopback assumptions that break job containers
- how to point job containers to the reachable Gitea host
- how to run the PR validation pipeline locally and through Gitea

5. Branch protection / PR policy docs
Create or update docs that define the required repository settings in Gitea:

- protect `main`
- require at least 1 approval
- dismiss stale approvals if supported
- block merge on rejected review if supported
- require all validation checks to pass
- no direct push to main
- merge only through PR after CI + human approval

This should be documented as the canonical Gitea policy for this repo.
Do not attempt to configure Gitea through unsupported automation if local docs are the safer path.

6. Validation and reporting
After implementation, run and report:
- workflow YAML sanity / parse validation if feasible
- local command validation for all jobs
- documentation consistency checks
- exact commands that operators should run

==================================================
WORKFLOW REQUIREMENTS
==================================================

The PR validation workflow must be professional and minimal.

Requirements:
- trigger on pull_request events
- use clear job names
- fail fast on broken setup
- avoid duplicated shell steps where practical
- keep jobs understandable to maintainers
- prefer explicit commands over hidden scripts unless scripts already exist in repo
- preserve local-first assumptions
- do not require external SaaS

Recommended job structure:
- lint
- types
- tests-unit
- tests-integration-redis

Each job should have:
- checkout
- Python setup if needed
- dependency install or environment bootstrap using the repo’s existing expected mechanism
- the exact validation command

If the repo already uses a `.context/.venv` pattern locally, do not assume that exact same path inside CI.
Create a CI-appropriate environment flow.

==================================================
NETWORKING / RUNNER SAFETY
==================================================

Be careful with Gitea runner networking.

The runner and job containers must be able to reach the Gitea instance correctly.

Do not assume `localhost` or loopback is valid inside job containers.
Document and implement a safe operator path that explains:
- reachable Gitea URL for runner/job containers
- runner registration expectations
- Docker-mode runner setup
- fallback notes if host networking is required locally

Do not hardcode machine-specific IPs in workflow logic unless confined to operator docs/examples.

==================================================
TEST COMMAND STANDARD
==================================================

Use the repository’s strongest current validation commands where applicable.

Target standards:
- ruff over critical Python sources
- mypy over `workspace`
- pytest over scheduler/tool tests
- pytest over Redis integration tests

If a command needs environment variables (for Redis port/db, etc.), encode that cleanly.

Do not hide important validation behind unclear wrappers unless a wrapper script already exists and is canonical.

==================================================
FILES TO CREATE OR UPDATE
==================================================

Likely targets:
- .gitea/workflows/pr-validation.yml
- README.md
- docs/local-validation.md
- docs/release-candidate.md
- docs/gitea-pr-validation.md   (create if needed)
- CONTRIBUTING.md
- WORKSPACE.md
- bootstrap/redis_diagnostics.py (only if alignment changes are needed)
- any minimal helper script if truly necessary

Do not rewrite unrelated runtime logic unless required to align commands/docs.

==================================================
NON-GOALS
==================================================

Do not:
- redesign scheduler
- redesign event model
- create GitHub-specific workflows
- add Gemini support
- add speculative CD/deploy stages
- add container publishing stages
- add meaningless badge or marketing changes
- weaken CI authority
- weaken human approval requirements

==================================================
ACCEPTANCE CRITERIA
==================================================

The work is complete only if all of the following are true:

1. `.gitea/workflows/pr-validation.yml` exists and is coherent.
2. The workflow covers lint, types, unit tests, and Redis integration tests.
3. The commands align with the repository’s actual validation stack.
4. Operator docs clearly explain:
   - enabling Actions
   - registering act_runner
   - Docker-mode recommendation
   - networking caveats
   - required branch protection settings
5. The docs clearly define the canonical PR gate:
   branch -> PR -> checks green -> human approval -> merge
6. No contradictory statements are introduced relative to AGENTS.md, CLAUDE.md, README.md, or existing guardrails.
7. Output includes exact commands and any assumptions.

==================================================
OUTPUT FORMAT
==================================================

At the end, print:

1. Summary of what was implemented
2. Files created or modified
3. The exact validation commands used by the PR workflow
4. The required Gitea repository settings for protected branches and PR gating
5. Any local environment assumptions
6. Validation performed

Do not leave TODO placeholders.
Do not propose future improvements.
Do not claim the workflow was executed in Gitea unless it actually was.
If something cannot be fully validated, state that precisely.