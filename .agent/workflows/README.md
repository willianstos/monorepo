# Local Workflows

This directory stores reusable operator workflows for the workspace.

Use it for step-by-step procedures that an engineer or coding agent may repeat, such as:

- release preparation
- incident response
- scheduler recovery
- environment bootstrap follow-ups
- migration checklists

## What Belongs Here

- concise Markdown playbooks
- repeatable operational sequences
- checklists tied to this repository's actual tooling and boundaries

## What Does Not Belong Here

- generic product documentation
- one-off scratch notes
- vendor manuals copied from external repositories
- agent skills that belong under `.agent/skills/`

## Quality Bar

- each workflow should have a clear trigger
- each workflow should define success and failure conditions
- each workflow should call out required approvals or dangerous steps
- each workflow should reference the real files, commands, and services involved

If a workflow cannot be executed repeatedly by someone else, it is still a note, not a workflow.
