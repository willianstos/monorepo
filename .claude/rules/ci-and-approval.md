# CI and Approval

CI and merge-gate policy is defined in [`AGENTS.md`](../../AGENTS.md). Claude-only reminders:

- Claude may assist CI analysis but does not replace CI outcomes.
- Reviewer analysis may block progress; merge authority remains with CI plus a human approver.
- Do not bypass the scheduler, the CI gate, or the human approval gate.
- Do not weaken tests to make CI pass.

## Gitea Networking — Hard Constraints

See canonical rule: [`.agent/rules/GITEA_NETWORKING.md`](../../.agent/rules/GITEA_NETWORKING.md).

- **`GITEA_ROOT_URL` must always be `http://172.17.0.1:3001/`** — never `localhost`.
- Never suggest `--add-host=localhost:...` in runner config as a fix for checkout failures — it does not work.
- Never replace `172.17.0.1` with a LAN IP in `ROOT_URL` or registration URLs.
- After any Gitea config change, verify with `docker exec gitea grep ROOT_URL /data/gitea/conf/app.ini`.
