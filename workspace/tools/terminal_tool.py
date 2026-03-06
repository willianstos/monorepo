from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ._policy import ToolAuditLogger, ToolExecutionError, ToolPolicyError

DISALLOWED_SHELL_TOKENS: tuple[str, ...] = ("&&", "||", ";", "|", "$(", "`")


@dataclass
class TerminalTool:
    allowed_commands: list[str] = field(default_factory=list)
    timeout_seconds: int = 60
    working_directory: Path = field(default_factory=Path.cwd)
    artifact_root: Path = field(default_factory=lambda: Path(".context") / "tool-audit")
    _audit: ToolAuditLogger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.working_directory = self.working_directory.resolve()
        self._audit = ToolAuditLogger("terminal_tool", self.artifact_root)

    def run(self, command: str) -> str:
        normalized = command.strip()
        if not normalized:
            raise self._policy_error("run", "Command must not be empty.", {"command": command})
        if any(token in normalized for token in DISALLOWED_SHELL_TOKENS):
            raise self._policy_error(
                "run",
                "Shell chaining and interpolation tokens are not allowed.",
                {"command": command},
            )

        argv = shlex.split(normalized, posix=False)
        executable = Path(argv[0]).name.lower()
        allowed = {name.lower() for name in self.allowed_commands}
        if executable not in allowed:
            raise self._policy_error(
                "run",
                f"Command '{argv[0]}' is not allowlisted.",
                {"command": command, "allowed_commands": sorted(allowed)},
            )

        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=self.working_directory,
                shell=False,
                check=False,
            )
        except FileNotFoundError as exc:
            raise self._execution_error(
                "run",
                f"Command '{argv[0]}' was not found on PATH.",
                {"command": command},
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise self._execution_error(
                "run",
                f"Command timed out after {self.timeout_seconds} seconds.",
                {"command": command},
            ) from exc

        artifact_path = self._audit.record(
            action="run",
            status="completed" if completed.returncode == 0 else "failed",
            details={
                "command": command,
                "argv": argv,
                "cwd": str(self.working_directory),
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )
        if completed.returncode != 0:
            raise ToolExecutionError(
                f"Command '{command}' failed with exit code {completed.returncode}. "
                f"Audit artifact: {artifact_path}"
            )
        return (completed.stdout or "").strip()

    def _policy_error(self, action: str, message: str, details: dict[str, object]) -> ToolPolicyError:
        artifact_path = self._audit.record(action=action, status="rejected", details=details | {"reason": message})
        return ToolPolicyError(f"{message} Audit artifact: {artifact_path}")

    def _execution_error(self, action: str, message: str, details: dict[str, object]) -> ToolExecutionError:
        artifact_path = self._audit.record(action=action, status="failed", details=details | {"reason": message})
        return ToolExecutionError(f"{message} Audit artifact: {artifact_path}")
