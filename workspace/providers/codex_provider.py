from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workspace.providers import ModelHandle


@dataclass(frozen=True)
class CodexProvider:
    name: str = "codex"
    interface: str = "cli"

    def describe_model(self, model_name: str, **options: Any) -> ModelHandle:
        return ModelHandle(provider=self.name, model=model_name, options=options)

    def build_client(self) -> Any:
        raise NotImplementedError("Codex CLI wiring is not implemented in this blueprint.")

