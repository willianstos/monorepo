from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class GenerationOptions:
    model: str
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_messages: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderResult:
    content: str
    provider: str
    model: str
    finish_reason: str = "stop"
    raw_output: str | None = None


class GatewayProvider(Protocol):
    name: str

    def generate(self, prompt: str, options: GenerationOptions) -> ProviderResult: ...

