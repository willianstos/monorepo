You are working inside 01-monorepo

This repository already has a local Gitea PR validation standard implemented and locally validated.
Your job now is NOT to redesign anything.
Your job is to operationalize and verify the activation path for local Gitea without introducing architecture drift.

Fixed repository truths that must remain unchanged:
- scheduler is a separate service
- Redis Streams is the only event/task bus
- DAG state persists in Redis
- agents communicate only through events
- CI is authoritative
- merge to main always requires human approval
- this is a local-first AI coding assistant workspace
- primary execution agents remain planner, coder, tester, reviewer

We are now doing the FINAL Gitea local activation pass.

==================================================
GOAL
==================================================

Prepare this repository for real activation inside a local Gitea instance using:

- Gitea Actions
- act_runner
- protected main branch
- required PR checks
- local-first reproducibility
- no bypass of CI or human approval

Do not claim that Gitea execution has happened unless it actually happens.
Do not invent cloud assumptions.
Do not weaken guardrails.

==================================================
TASKS
==================================================

1. Audit the current Gitea PR validation assets

Inspect and verify:
- .gitea/workflows/pr-validation.yml
- docs/gitea-pr-validation.md
- README.md
- CONTRIBUTING.md
- WORKSPACE.md
- docs/release-candidate.md

Confirm they are internally consistent with:
- AGENTS.md
- CLAUDE.md
- GUARDRAILS.md

2. Produce a single operator-grade activation checklist

Create or update:

docs/gitea-activation-checklist.md

This file must be the canonical step-by-step activation guide.

It must include exact steps for:

A. Gitea prerequisites
- confirm Actions are enabled
- identify whether runner scope will be repository-level, org-level, or instance-level
- locate where the runner registration token must be obtained

B. act_runner activation
- Docker-based runner path as the recommended standard
- exact registration command examples
- exact daemon start approach
- note that localhost/loopback assumptions may break inside containers
- explain that the runner/job containers must reach the real Gitea URL

C. First workflow activation
- push branch
- open PR
- wait for workflow
- capture the exact job names reported by Gitea
- confirm they match the branch protection required status checks

D. Branch protection activation
Document the exact Gitea settings required for main:
- no direct push
- merge only by PR
- at least 1 approval
- dismiss stale approvals if available
- block merge on rejected reviews if available
- block merge on official review requests if available
- require status checks to pass
- block merge if branch is outdated if available

E. Validation after activation
- confirm all workflow jobs are green
- confirm merge is blocked if checks fail
- confirm merge is blocked before human approval
- confirm merge becomes possible only after checks pass and approval exists

3. Add a practical command section

In docs/gitea-activation-checklist.md include exact commands/examples for:

- validating workflow YAML locally if applicable
- starting local Redis validation path
- registering the runner
- starting runner daemon
- opening the first PR validation test
- inspecting workflow results
- identifying exact status check names to copy into branch protection

Do not hardcode machine-specific secrets or tokens.
Use placeholders where sensitive data would appear.

4. Create a first-run verification section

Document an explicit “first successful PR run” checklist with pass/fail items:
- workflow appears in Gitea
- runner picks up jobs
- lint passes
- mypy passes
- unit tests pass
- Redis integration tests pass
- merge remains blocked until approval
- merge remains blocked if checks are red

5. Create a troubleshooting section

Add a concise troubleshooting section covering:
- runner registered but idle
- jobs cannot reach Gitea
- status checks not visible in branch protection
- Redis integration job failing due to environment setup
- branch protection not blocking merge because required check names do not match actual job names

6. Keep output practical

Do not add speculative improvements.
Do not add cloud/CD topics.
Do not redesign workflows.
Do not change runtime architecture unless a tiny correction is necessary for consistency.

==================================================
OUTPUT FORMAT
==================================================

At the end, print:

1. Summary of what was verified
2. Files created or modified
3. The final activation checklist path
4. Exact operator actions to perform next in Gitea UI and on the runner host
5. Any assumptions that still require a real Gitea execution to confirm
6. Validation performed

If something cannot be confirmed without a live Gitea execution, state that explicitly instead of guessing.