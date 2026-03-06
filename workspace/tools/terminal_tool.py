from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TerminalTool:
    allowed_commands: list[str] = field(default_factory=list)
    timeout_seconds: int = 60

    def run(self, command: str) -> str:
        raise NotImplementedError("Terminal execution is not implemented in this blueprint.")

