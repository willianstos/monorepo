from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ._policy import ToolAuditLogger, ToolExecutionError, ToolPolicyError


@dataclass
class GitTool:
    repo_root: Path
    timeout_seconds: int = 60
    artifact_root: Path = field(default_factory=lambda: Path(".context") / "tool-audit")
    _audit: ToolAuditLogger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.repo_root = self.repo_root.resolve()
        self._audit = ToolAuditLogger("git_tool", self.artifact_root)

    def status(self) -> str:
        return self._run_git(["status", "--short"], action="status")

    def diff(self, target: str = "HEAD") -> str:
        return self._run_git(["diff", target], action="diff", metadata={"target": target})

    def commit(self, message: str) -> str:
        if not message.strip():
            raise self._policy_error("commit", "Commit message must not be empty.", {"message": message})
        return self._run_git(["commit", "-m", message], action="commit", metadata={"message": message})

    def _run_git(self, argv: list[str], *, action: str, metadata: dict[str, str] | None = None) -> str:
        if not (self.repo_root / ".git").exists():
            raise self._policy_error(
                action,
                f"Path '{self.repo_root}' is not a Git repository.",
                {"repo_root": str(self.repo_root)},
            )

        completed = subprocess.run(
            ["git", *argv],
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            cwd=self.repo_root,
            shell=False,
            check=False,
        )
        artifact_path = self._audit.record(
            action=action,
            status="completed" if completed.returncode == 0 else "failed",
            details={
                "repo_root": str(self.repo_root),
                "argv": ["git", *argv],
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                **(metadata or {}),
            },
        )
        if completed.returncode != 0:
            raise ToolExecutionError(
                f"Git action '{action}' failed with exit code {completed.returncode}. "
                f"Audit artifact: {artifact_path}"
            )
        return (completed.stdout or "").strip()

    def _policy_error(self, action: str, message: str, details: dict[str, str]) -> ToolPolicyError:
        artifact_path = self._audit.record(action=action, status="rejected", details=details | {"reason": message})
        return ToolPolicyError(f"{message} Audit artifact: {artifact_path}")
