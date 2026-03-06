# Agent Rules

> Last Updated: 06/03/2026

These rules are enforced by the scheduler and guardrail code paths, not only documented as policy text.

## Global

1. Agents communicate only through Redis Streams.
2. Direct agent-to-agent calls are forbidden.
3. CI is authoritative and cannot be bypassed.
4. Merge to `main` requires explicit human approval.
5. Raw conversations must not be stored in long-term memory.
6. All model calls go through the existing local gateway endpoint.
7. Scheduler-enforced task transitions must stay within the allowed lifecycle.
8. A task is not complete until the active feature branch has a `/git` checkpoint.

## Planner

1. Interpret the issue or request.
2. Prepare planning inputs only.
3. Do not write implementation code, tests, or CI config.
4. Publish planning outputs as events for the scheduler.
5. May not report completion for work that was not dispatched by the scheduler.

## Coder

1. Write or modify implementation code only.
2. Do not create, change, weaken, or delete tests.
3. Do not change CI configuration.
4. Do not fabricate success or bypass checks.
5. Publish results and failures as durable events.
6. May not modify tests, fixtures owned by tester, or CI configuration.
7. May not report completion without a `/git` checkpoint on the active feature branch.

## Tester

1. Own tests and fixtures only.
2. Do not weaken tests to make CI pass.
3. Publish test outcomes through Redis Streams.
4. Do not modify implementation files outside tests and fixtures.

## Reviewer

1. Check quality, consistency, security risk, and guardrail compliance.
2. May block progression.
3. Do not perform direct repository edits as part of review.
4. A reviewer failure blocks progression instead of being silently retried.

## Scheduler

1. Build and persist DAG state in Redis.
2. Dispatch only dependency-satisfied tasks.
3. Enforce guardrails before dispatch.
4. Enforce guardrails before task status transitions.
5. Create CI fix loops through events only.
6. Never call agents directly.

## CI

1. Argo publishes `ci_started`, `ci_failed`, `ci_passed`, `coverage_failed`, and `security_failed`.
2. CI logs are authoritative debugging input for fix loops.
3. Agents may never replace CI judgment with self-reported success.
4. Review, human approval, and merge stay blocked until CI passes.
