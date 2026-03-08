# Worktree Policy

Last Updated: 08/03/2026

Status: accepted in Phase R on 2026-03-06 and standardized for operator use on 08/03/2026.

## Purpose

Define the safe default worktree policy for isolated coding tasks without changing the repository control model.

This policy now covers both:

- scheduler/DAG-driven mutable isolation
- operator/CLI mutable isolation in WSL

## Required Use

A dedicated worktree is required when all of the following are true:

- the task will modify tracked files
- the task belongs to a specific DAG or fix loop
- another mutable task may run concurrently against the same repository

A dedicated worktree is also required for:

- mutable retry and fix-loop work so that failed state does not contaminate the primary checkout
- operator-driven feature work when another mutable task may run in parallel

## Optional Use

A worktree is optional for:

- read-only planning
- read-only review
- read-only status or telemetry inspection
- single-operator local debugging in a non-concurrent scenario

The primary checkout is the default operator baseline only when the mutable task is singular and short-lived.

## Isolation Mapping

- One active mutable task gets one worktree.
- Worktrees are not shared between active tasks or between primary agents.
- Scheduler/DAG branch naming uses the task identity:
  - `fa/<graph-id>/<task-id>`
- Operator/CLI branch naming uses the dated feature pattern:
  - `feature/<yyyymmdd>-<slug>-<random>`
- The standard worktree path lives outside the primary checkout:
  - Scheduler/DAG path: `../.worktrees/<repo-name>/<graph-id>/<task-id>`
  - Operator/CLI path: `../.worktrees/<repo-name>/<yyyymmdd>/<branch-name>`

## Safety Rules

1. Do not edit a mutable task in the primary checkout when that task is assigned a worktree.
2. Do not reuse a worktree across different DAGs.
3. Do not reuse a task branch for a new graph.
4. Do not commit directly to `main`.
5. Do not allow one worktree to carry changes for multiple independent tasks.
6. Capture evidence before cleanup if the task failed and the operator requests retention.
7. Use WSL as the authoring side for operator worktree creation and mutation.
8. Treat a worktree as a sandbox, not as an alternate authority lane.

## Cleanup Policy

- Create the worktree immediately before mutable task execution starts.
- Remove the worktree when the task reaches a terminal state and no retention flag is active.
- Remove retained failure worktrees after evidence capture or explicit operator release.
- Prune stale worktrees during scheduler recovery or operator maintenance if the owning DAG is terminal or missing.
- For operator worktree branches, remove the worktree after merge, abandonment, or branch supersession.

## Operator Standard

Baseline on 08/03/2026:

- author from WSL
- keep the primary checkout as the stable baseline
- use a dedicated worktree for concurrent mutable work
- create operator worktrees with `bash bootstrap/git-worktree.sh create "dd/mm/aaaa" "branch-slug"`
- checkpoint and sync branch work with `/git`

## PR And CI Interaction

- Worktrees are local execution sandboxes only.
- CI authority, PR flow, and human approval rules do not change.
- Changes still move through the existing branch -> commit -> CI -> review -> human approval -> merge path.
- A worktree does not create an alternate merge unit, alternate review channel, or alternate approval path.
