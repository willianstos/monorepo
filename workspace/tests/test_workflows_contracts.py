"""Contract consistency checks for canonical workflow documents."""

from __future__ import annotations

from pathlib import Path

from workspace.tests.workflow_validation_helpers import contains_phrase, load_policy_corpus, read_text

WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".agent" / "workflows"


def _workflow_text(name: str) -> str:
    return read_text(WORKFLOWS_DIR / f"{name}.md").lower()


def test_canonical_policy_text_covers_core_truths() -> None:
    policy = load_policy_corpus()

    # Core execution and hosting authority.
    assert contains_phrase(policy["agents"], "ci: authoritative")
    assert contains_phrase(policy["agents"], "merge to `main`")
    assert contains_phrase(policy["agents"], "human approval")
    assert contains_phrase(policy["guardrails"], "ci is authoritative")
    assert contains_phrase(policy["guardrails"], "merge to `main`")
    assert contains_phrase(policy["guardrails"], "human approval")
    assert contains_phrase(policy["workspace"], "git and pr policy")
    assert contains_phrase(policy["workspace"], "docs/guide_git.md")
    assert contains_phrase(policy["workspace"], "docs/gitea-pr-validation.md")

    # Authoritative Git model:
    assert contains_phrase(policy["gitea"], "local gitea is the authoritative host")
    assert contains_phrase(policy["gitea"], "github is mirror-only")
    assert contains_phrase(policy["gitea"], "pr gate on the authoritative host")
    assert contains_phrase(policy["gitea"], "no merge without both passing ci and explicit human approval")
    assert contains_phrase(policy["gitea"], "feature branch")
    assert contains_phrase(policy["gitea"], "require status checks")
    assert contains_phrase(policy["gitea"], "required approvals")

    # Canonical git guide carries repository-specific truth language.
    assert contains_phrase(policy["git_guide"], "gitea")
    assert contains_phrase(policy["git_guide"], "autoritativo")
    assert contains_phrase(policy["git_guide"], "github")
    assert contains_phrase(policy["git_guide"], "mirror") or contains_phrase(policy["git_guide"], "espelho")
    assert contains_phrase(policy["git_guide"], "main")
    assert contains_phrase(policy["git_guide"], "canônica")


def test_git_workflow_contract_is_not_a_pr_replacement() -> None:
    content = _workflow_text("git")

    assert "bootstrap/git-cycle.sh" in content
    assert "does not replace" in content
    assert "--merge-main" in content
    assert "pr" in content
    assert "origin" in content and "github" in content
    assert "push" in content
    assert "no default merge" in content
    assert "replacement for /pr" not in content

    forbidden = [
        "merge to main by default",
        "auto-merge",
        "without pr",
        "direct push to main",
    ]
    for phrase in forbidden:
        assert phrase not in content


def test_pr_workflow_contract_reinforces_ci_and_human_approval() -> None:
    content = _workflow_text("pr")

    assert "docs/gitea-pr-validation.md" in content
    assert "ci" in content
    assert "human approval" in content or "human" in content and "approval" in content
    assert "branch -> commit -> ci -> review -> human approval -> merge" in content


def test_validate_workflow_contract_reinforces_local_gate_only() -> None:
    content = _workflow_text("validate")
    policy = load_policy_corpus()

    assert "local-validation.md" in content
    assert "local" in content
    assert "local-only" in content
    assert "remote ci" in content or "remote ci bypass" in content

    expected_commands = [
        "python -m ruff check workspace projects",
        "python -m mypy workspace",
        "python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q",
        "python -m pytest workspace/scheduler/test_redis_integration.py -q",
    ]

    for command in expected_commands:
        assert command in content
        assert command in policy["gitea"] or command in policy["local_validation"]

    # Explicit ban: this is not a CI bypass for merge decisions.
    assert "ci bypass" not in content


def test_release_note_and_workflow_map_contract_checks() -> None:
    release_note_text = _workflow_text("release-note")
    workflow_map_text = _workflow_text("workflow-map")

    assert "guardrails" in release_note_text
    assert "diff analysis" in release_note_text
    assert "context retrieval" in release_note_text
    assert "agents.md" in release_note_text

    assert "source read" in workflow_map_text
    assert "verification" in workflow_map_text
    assert "agents.md" in workflow_map_text

    forbidden = [
        "replace ci",
        "merge to main without pr",
        "auto-approve",
    ]
    for phrase in forbidden:
        assert phrase not in release_note_text
        assert phrase not in workflow_map_text


def test_validate_workflow_commands_match_pr_validation_pipeline() -> None:
    pr_validation_text = read_text(
        Path(__file__).resolve().parents[2] / "docs" / "gitea-pr-validation.md"
    ).lower()

    assert "python -m ruff check workspace projects" in pr_validation_text
    assert "python -m mypy workspace" in pr_validation_text
    assert "python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q" in pr_validation_text
    assert "python -m pytest workspace/scheduler/test_redis_integration.py -q" in pr_validation_text
