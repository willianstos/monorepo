# CI and Approval

CI and merge-gate policy is defined in [`AGENTS.md`](../../AGENTS.md). Claude-only reminders:

- Claude may assist CI analysis but does not replace CI outcomes.
- Reviewer analysis may block progress; merge authority remains with CI plus a human approver.
- Do not bypass the scheduler, the CI gate, or the human approval gate.
- Do not weaken tests to make CI pass.
