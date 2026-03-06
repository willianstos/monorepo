from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FilesystemTool:
    root: Path

    def read_text(self, path: str) -> str:
        raise NotImplementedError("Filesystem reads are not implemented in this blueprint.")

    def write_text(self, path: str, content: str) -> None:
        raise NotImplementedError("Filesystem writes are not implemented in this blueprint.")

    def list_files(self, relative_path: str = ".") -> list[str]:
        raise NotImplementedError("Filesystem listing is not implemented in this blueprint.")

