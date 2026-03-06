from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ToolPolicyError(RuntimeError):
    """Raised when a tool request exceeds the declared policy or scope."""


class ToolExecutionError(RuntimeError):
    """Raised when an in-policy tool action fails during execution."""


@dataclass(frozen=True)
class ToolAuditLogger:
    tool_name: str
    artifact_root: Path = field(default_factory=lambda: Path(".context") / "tool-audit")

    def record(self, *, action: str, status: str, details: dict[str, Any]) -> Path:
        target_dir = self.artifact_root / self.tool_name
        target_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = target_dir / f"{self._timestamp()}-{action}-{status}.json"
        payload = {
            "tool": self.tool_name,
            "action": action,
            "status": status,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }
        artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return artifact_path

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def resolve_scoped_path(root: Path, raw_path: str) -> Path:
    if not raw_path.strip():
        raise ToolPolicyError("Tool path must not be empty.")

    scoped_root = root.resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = scoped_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(scoped_root)
    except ValueError as exc:
        raise ToolPolicyError(
            f"Path '{raw_path}' escapes the allowed root '{scoped_root}'."
        ) from exc
    return resolved
