# Worktree Policy

Status: accepted in Phase R on 2026-03-06

## Purpose

Define a minimal, safe worktree policy for isolated coding tasks without changing the repository control model.

## Required Use

A dedicated worktree is required when all of the following are true:

- the task will modify tracked files
- the task belongs to a specific DAG or fix loop
- another mutable task may run concurrently against the same repository

A dedicated worktree is also required for mutable retry and fix-loop work so that failed state does not contaminate the primary checkout.

## Optional Use

A worktree is optional for:

- read-only planning
- read-only review
- read-only status or telemetry inspection
- single-operator local debugging in a non-concurrent scenario

## Isolation Mapping

- One active mutable DAG task gets one worktree.
- Worktrees are not shared between active tasks or between primary agents.
- Branch naming uses the task identity, not a long-lived shared branch:
  - `fa/<graph-id>/<task-id>`
- The worktree path must live outside the primary checkout:
  - `../.worktrees/<repo-name>/<graph-id>/<task-id>`

## Safety Rules

1. Do not edit a mutable task in the primary checkout when that task is assigned a worktree.
2. Do not reuse a worktree across different DAGs.
3. Do not reuse a task branch for a new graph.
4. Do not commit directly to `main`.
5. Do not allow one worktree to carry changes for multiple independent tasks.
6. Capture evidence before cleanup if the task failed and the operator requests retention.

## Cleanup Policy

- Create the worktree immediately before mutable task execution starts.
- Remove the worktree when the task reaches a terminal state and no retention flag is active.
- Remove retained failure worktrees after evidence capture or explicit operator release.
- Prune stale worktrees during scheduler recovery or operator maintenance if the owning DAG is terminal or missing.

## PR And CI Interaction

- Worktrees are local execution sandboxes only.
- CI authority, PR flow, and human approval rules do not change.
- Changes still move through the existing branch -> commit -> CI -> review -> human approval -> merge path.
- A worktree does not create an alternate merge unit, alternate review channel, or alternate approval path.
