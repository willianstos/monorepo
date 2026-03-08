"""Simulation-only validation checks for workflow docs and script behavior."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from .workflow_validation_helpers import DOCS, read_text, workflow_path


REPO_ROOT = Path(__file__).resolve().parents[2]
GIT_SCRIPT = REPO_ROOT / "bootstrap" / "git-cycle.sh"

def _run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_required(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = _run(command, cwd=cwd, env=env)
    if result.returncode:
        raise RuntimeError(f"Command failed ({command[0]}): {result.stderr}")
    return result


def _run_git_cycle(
    repository: Path,
    *,
    merge_main: bool = False,
    date_label: str = "07/03/2026",
    branch_name: str = "smoke-git-cycle",
) -> subprocess.CompletedProcess[str]:
    cmd = [str(GIT_SCRIPT), "--dry-run"]
    if merge_main:
        cmd.append("--merge-main")
    cmd.extend([date_label, branch_name])

    env = os.environ.copy()
    # Allow execution outside WSL in CI and test shells.
    env["BOOTSTRAP_GIT_CYCLE_ALLOW_NON_WSL"] = "1"

    return _run(cmd, cwd=repository, env=env)


def _make_sandbox_repo(branch_name: str = "feature/smoke-git-workflow") -> Path:
    base = Path(tempfile.mkdtemp(prefix="workflow-git-smoke-"))
    origin = base / "origin.git"
    github = base / "github.git"

    _run_required(["git", "init", "--bare", str(origin)])
    _run_required(["git", "init", "--bare", str(github)])

    repo = base / "repo"
    _run_required(["git", "init", "-b", "main", str(repo)])

    # Ensure git metadata is stable inside disposable repos.
    _run_required(["git", "config", "user.name", "test-user"], cwd=repo)
    _run_required(["git", "config", "user.email", "test-user@example.com"], cwd=repo)

    readme = repo / "README.md"
    readme.write_text("workflow smoke baseline\n", encoding="utf-8")
    _run_required(["git", "add", "README.md"], cwd=repo)
    _run_required([
        "git",
        "commit",
        "-m",
        "chore(repo): bootstrap main for workflow smoke",
    ], cwd=repo)

    _run_required(["git", "remote", "add", "origin", str(origin)], cwd=repo)
    _run_required(["git", "remote", "add", "github", str(github)], cwd=repo)

    _run_required(["git", "push", "-u", "origin", "main"], cwd=repo)
    _run_required(["git", "push", "-u", "github", "main"], cwd=repo)

    _run_required(["git", "switch", "-c", branch_name], cwd=repo)
    return repo


def test_git_workflow_simulation_is_dry_run_and_safe() -> None:
    workflow_text = read_text(workflow_path("git")).lower()
    assert "bootstrap/git-cycle.sh" in workflow_text

    branch_name = "feature-safe-smoke"
    sandbox = _make_sandbox_repo(branch_name=branch_name)

    result = _run_git_cycle(
        sandbox,
        merge_main=False,
        date_label="06/03/2026",
        branch_name=branch_name,
    )
    assert result.returncode == 0
    output = (result.stdout + result.stderr).lower()

    assert "git fetch origin --prune" in output
    assert "git fetch github --prune" in output
    assert f"git push -u origin {branch_name}" in output
    assert f"git push github {branch_name}" in output
    assert "git switch main" not in output
    assert "git merge --no-ff" not in output

    merged = _run_git_cycle(
        sandbox,
        merge_main=True,
        date_label="06/03/2026",
        branch_name=branch_name,
    )
    assert merged.returncode == 0
    merge_output = (merged.stdout + merged.stderr).lower()

    assert "git switch main" in merge_output
    assert "git pull --ff-only origin main" in merge_output
    assert f"git merge --no-ff {branch_name} -m" in merge_output
    assert "git push origin main" in merge_output
    assert "git push github main" in merge_output


def test_validate_workflow_simulation_and_command_consistency() -> None:
    validate_text = read_text(workflow_path("validate")).lower()

    required_commands = [
        "python -m ruff check workspace projects",
        "python -m mypy workspace",
        "python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q",
        "python -m pytest workspace/scheduler/test_redis_integration.py -q",
    ]

    for command in required_commands[:4]:
        assert command in validate_text

    # Validate command references use real, local repo targets.
    for file_path in [
        REPO_ROOT / "workspace" / "scheduler" / "test_orchestration.py",
        REPO_ROOT / "workspace" / "tools" / "test_policies.py",
        REPO_ROOT / "workspace" / "scheduler" / "test_redis_integration.py",
    ]:
        assert file_path.exists(), f"Referenced test file not found: {file_path}"

    gitea_policy_text = DOCS["gitea"].read_text(encoding="utf-8").lower()
    assert "python -m ruff check workspace projects" in gitea_policy_text
    assert "python -m mypy workspace" in gitea_policy_text
    assert "python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q" in gitea_policy_text
    assert "python -m pytest workspace/scheduler/test_redis_integration.py -q" in gitea_policy_text

    # Validate that the documented `python -m ...` commands can run under the
    # active interpreter even when the virtualenv is invoked without activation.
    assert Path(sys.executable).exists()
    assert Path(sys.executable).name.startswith("python")


def test_git_cycle_script_passes_shellcheck_when_available() -> None:
    if shutil.which("shellcheck") is None:
        pytest.skip("ShellCheck not installed in test environment")

    result = _run(["shellcheck", "-x", str(GIT_SCRIPT)], cwd=REPO_ROOT)
    assert result.returncode == 0, result.stderr


def test_pr_workflow_simulation_is_contractual() -> None:
    text = read_text(workflow_path("pr")).lower()
    assert "docs/gitea-pr-validation.md" in text
    assert "feature branch" in text
    assert "ci" in text
    assert "human approval" in text or "aprovação humana" in text


def test_release_note_and_workflow_map_simulation_checks() -> None:
    release_text = read_text(workflow_path("release-note")).lower()
    workflow_map_text = read_text(workflow_path("workflow-map")).lower()

    assert "diff analysis" in release_text
    assert "context retrieval" in release_text

    assert "source read" in workflow_map_text
    assert "abstraction" in workflow_map_text
    assert "agent" in workflow_map_text
