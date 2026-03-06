from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class GitTool:
    repo_root: Path

    def status(self) -> str:
        raise NotImplementedError("Git status execution is not implemented in this blueprint.")

    def diff(self, target: str = "HEAD") -> str:
        raise NotImplementedError("Git diff execution is not implemented in this blueprint.")

    def commit(self, message: str) -> str:
        raise NotImplementedError("Git commit execution is not implemented in this blueprint.")

