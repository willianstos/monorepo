from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ._policy import ToolAuditLogger, ToolExecutionError, ToolPolicyError, resolve_scoped_path


@dataclass
class FilesystemTool:
    root: Path
    artifact_root: Path = field(default_factory=lambda: Path(".context") / "tool-audit")
    _audit: ToolAuditLogger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.root = self.root.resolve()
        self._audit = ToolAuditLogger("filesystem_tool", self.artifact_root)

    def read_text(self, path: str) -> str:
        target = self._resolve_path(path, action="read_text")
        try:
            content = target.read_text(encoding="utf-8")
        except OSError as exc:
            raise self._execution_error(
                "read_text",
                f"Filesystem read failed for '{path}': {exc}",
                {"path": path},
            ) from exc

        self._audit.record(
            action="read_text",
            status="completed",
            details={"path": str(target), "size_bytes": len(content.encode("utf-8"))},
        )
        return content

    def write_text(self, path: str, content: str) -> None:
        target = self._resolve_path(path, action="write_text")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise self._execution_error(
                "write_text",
                f"Filesystem write failed for '{path}': {exc}",
                {"path": path},
            ) from exc

        self._audit.record(
            action="write_text",
            status="completed",
            details={"path": str(target), "size_bytes": len(content.encode("utf-8"))},
        )

    def list_files(self, relative_path: str = ".") -> list[str]:
        target = self._resolve_path(relative_path, action="list_files")
        if not target.exists():
            raise self._execution_error(
                "list_files",
                f"Path '{relative_path}' does not exist.",
                {"path": relative_path},
            )

        if target.is_file():
            entries = [target.relative_to(self.root).as_posix()]
        else:
            entries = sorted(path.relative_to(self.root).as_posix() for path in target.iterdir())

        self._audit.record(
            action="list_files",
            status="completed",
            details={"path": str(target), "entry_count": len(entries)},
        )
        return entries

    def _resolve_path(self, path: str, *, action: str) -> Path:
        try:
            return resolve_scoped_path(self.root, path)
        except ToolPolicyError as exc:
            raise self._policy_error(action, str(exc), {"path": path}) from exc

    def _policy_error(self, action: str, message: str, details: dict[str, str]) -> ToolPolicyError:
        artifact_path = self._audit.record(action=action, status="rejected", details=details | {"reason": message})
        return ToolPolicyError(f"{message} Audit artifact: {artifact_path}")

    def _execution_error(self, action: str, message: str, details: dict[str, str]) -> ToolExecutionError:
        artifact_path = self._audit.record(action=action, status="failed", details=details | {"reason": message})
        return ToolExecutionError(f"{message} Audit artifact: {artifact_path}")
