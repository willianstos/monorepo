# CI And Approval

- CI is authoritative. Claude may assist analysis, but it does not replace CI outcomes.
- Do not push directly to `main`.
- Merge to `main` requires passing CI and explicit human approval.
- Do not bypass the scheduler, the CI gate, or the human approval gate.
- Do not weaken tests to make CI pass.
- Reviewer analysis may block progress, but merge authority still remains with CI plus a human approver.
