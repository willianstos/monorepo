from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from workspace.providers.model_auditor import ModelAuditResult, ModelInfrastructureAuditor

BackendType = Literal["local_api", "oauth_cli"]
TransportType = Literal["ollama", "cli"]


@dataclass(frozen=True)
class ModelRouteDecision:
    task_type: str
    provider: str
    model: str
    backend_type: BackendType
    transport: TransportType
    target: str
    reason: str
    confidence: float


class ModelRouter:
    """Translate audit results or explicit model aliases into concrete backend routes."""

    def __init__(self, auditor: ModelInfrastructureAuditor | None = None) -> None:
        self.auditor = auditor or ModelInfrastructureAuditor()

    def route_task(self, task_description: str, model_override: str | None = None) -> ModelRouteDecision:
        if model_override and model_override not in {"auto", "gateway-auto"}:
            return self._route_from_alias(model_override)

        audit = self.auditor.audit(task_description)
        return self._route_from_audit(audit)

    def _route_from_audit(self, audit: ModelAuditResult) -> ModelRouteDecision:
        return self._route_from_alias(
            audit["recommended_model"],
            task_type=audit["task_type"],
            reason=audit["reason"],
            confidence=audit["confidence"],
        )

    def _route_from_alias(
        self,
        alias: str,
        *,
        task_type: str | None = None,
        reason: str | None = None,
        confidence: float | None = None,
    ) -> ModelRouteDecision:
        normalized = alias.strip().lower()

        if normalized in {"local", "qwen3.5:9b", "local:qwen3.5:9b"}:
            return ModelRouteDecision(
                task_type=task_type or "helper_task",
                provider="local",
                model="qwen3.5:9b",
                backend_type="local_api",
                transport="ollama",
                target="http://localhost:11434/api/generate",
                reason=reason or "Explicit local override.",
                confidence=confidence if confidence is not None else 1.0,
            )

        if normalized in {"codex", "codex-cli"}:
            return ModelRouteDecision(
                task_type=task_type or "implementation",
                provider="codex",
                model="codex-cli",
                backend_type="oauth_cli",
                transport="cli",
                target="codex exec",
                reason=reason or "Explicit Codex override.",
                confidence=confidence if confidence is not None else 1.0,
            )

        if normalized in {"claude", "claude-code"}:
            return ModelRouteDecision(
                task_type=task_type or "planning",
                provider="claude",
                model="claude-code",
                backend_type="oauth_cli",
                transport="cli",
                target="claude",
                reason=reason or "Explicit Claude override.",
                confidence=confidence if confidence is not None else 1.0,
            )

        raise ValueError(f"Unsupported model alias '{alias}' for the repository standard.")
