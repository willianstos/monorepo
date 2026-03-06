"""Provider abstractions for pluggable LLM backends."""

# ruff: noqa: E402

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ModelHandle:
    provider: str
    model: str
    options: dict[str, Any]


class ProviderAdapter(Protocol):
    name: str

    def describe_model(self, model_name: str, **options: Any) -> ModelHandle: ...

    def build_client(self) -> Any: ...


from .anthropic_provider import AnthropicProvider
from .claude_provider import ClaudeProvider
from .codex_provider import CodexProvider
from .gemini_provider import GeminiProvider
from .local_provider import LocalProvider
from .model_auditor import ModelAuditResult, ModelInfrastructureAuditor
from .model_router import ModelRouteDecision, ModelRouter
from .openai_provider import OpenAIProvider


__all__ = [
    "AnthropicProvider",
    "ClaudeProvider",
    "CodexProvider",
    "GeminiProvider",
    "LocalProvider",
    "ModelAuditResult",
    "ModelHandle",
    "ModelInfrastructureAuditor",
    "ModelRouteDecision",
    "ModelRouter",
    "OpenAIProvider",
    "ProviderAdapter",
]
