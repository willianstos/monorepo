from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ProviderExecutionError(RuntimeError):
    """Raised when a provider command cannot complete safely."""


@dataclass(frozen=True)
class CLISandboxExecutor:
    allowed_commands: tuple[str, ...] = ("codex", "claude", "gemini")
    timeout_seconds: int = 180

    def run(
        self,
        command_prefix: list[str],
        *,
        prompt: str,
        extra_env: dict[str, str] | None = None,
    ) -> str:
        if not command_prefix:
            raise ProviderExecutionError("Missing CLI command prefix.")

        executable = Path(command_prefix[0]).name.lower()
        if executable not in self.allowed_commands:
            raise ProviderExecutionError(f"Command '{command_prefix[0]}' is not allowlisted.")

        env = self._build_safe_env(extra_env or {})

        try:
            completed = subprocess.run(
                command_prefix,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
                env=env,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ProviderExecutionError(f"Command not found: {command_prefix[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ProviderExecutionError(f"Command timed out: {' '.join(command_prefix)}") from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise ProviderExecutionError(
                f"Provider command failed with exit code {completed.returncode}: {stderr}"
            )

        return (completed.stdout or "").strip()

    def parse_command(self, env_var: str, default: str) -> list[str]:
        command = os.getenv(env_var, default)
        return shlex.split(command, posix=False)

    def _build_safe_env(self, extra_env: dict[str, str]) -> dict[str, str]:
        allowlist = {
            "APPDATA",
            "HOME",
            "HOMEDRIVE",
            "HOMEPATH",
            "LOCALAPPDATA",
            "PATH",
            "PATHEXT",
            "SYSTEMDRIVE",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "USERPROFILE",
        }
        env = {key: value for key, value in os.environ.items() if key.upper() in allowlist}
        env.update(extra_env)
        return env

