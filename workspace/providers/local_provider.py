from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workspace.providers import ModelHandle


@dataclass(frozen=True)
class LocalProvider:
    name: str = "local"
    runtime: str = "ollama"
    endpoint: str | None = None

    def describe_model(self, model_name: str, **options: Any) -> ModelHandle:
        return ModelHandle(provider=self.name, model=model_name, options=options)

    def build_client(self) -> Any:
        raise NotImplementedError("Local provider wiring is not implemented in this blueprint.")
