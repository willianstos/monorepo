from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from workspace.event_bus import RedisStreamBus
from workspace.gateway.router import GatewayRouter
from workspace.memory import MemoryManager, MemoryRuntimeService
from workspace.providers.model_auditor import ModelInfrastructureAuditor
from workspace.providers.model_router import ModelRouter
from workspace.scheduler import SchedulerService


@dataclass
class AssistantRuntime:
    """Runtime bootstrap for the local-first assistant workspace and scheduler service."""

    workspace_root: Path
    context_root: Path | None = None
    rules_root: Path | None = None

    def __post_init__(self) -> None:
        if self.context_root is None:
            self.context_root = self.workspace_root.parent / ".context"
        if self.rules_root is None:
            self.rules_root = self.workspace_root.parent / "guardrails"

    def bootstrap(self) -> dict[str, Any]:
        scheduler = SchedulerService.build_default(rules_root=self.rules_root)
        memory_runtime = MemoryRuntimeService.build_default(rules_root=self.rules_root)
        gateway_router = GatewayRouter()
        bus = RedisStreamBus()
        auditor = ModelInfrastructureAuditor()
        router = ModelRouter(auditor=auditor)
        memory = MemoryManager()
        scheduler.ensure_groups()
        memory_runtime.ensure_group()

        connection_available = False
        connection_error: str | None = None
        try:
            connection_available = bus.ping()
        except Exception as exc:  # pragma: no cover - environment dependent
            connection_error = str(exc)

        return {
            "runtime": "assistant_runtime",
            "phase": "implementation",
            "workspace_root": str(self.workspace_root),
            "context_root": str(self.context_root),
            "guardrails_root": str(self.rules_root),
            "scheduler": scheduler.describe(),
            "event_bus": {
                "backend": "redis_streams",
                "connection": bus.connection_info(),
                "durable": True,
                "consumer_groups": True,
                "connection_available": connection_available,
                "connection_error": connection_error,
            },
            "gateway": {
                "endpoint": "http://localhost:4000/v1/chat/completions",
                "providers": sorted(gateway_router._providers.keys()),
            },
            "model_policy": {
                "model_agnostic_scheduler": True,
                "sample_route": router.route_task("Summarize CI logs").model,
                "local_first": True,
            },
            "memory": {
                "layers": memory.memory_layers(),
                "retrieval_order": list(memory.retrieval_order()),
                "guardrail_rules": memory.flush([])["rules"],
                "runtime_write_path": memory_runtime.describe(),
            },
            "guardrail_validation": {
                "scheduler": scheduler.guardrails.dry_run_validation(),
                "memory_payload_allowed": scheduler.guardrails.validate_memory_payload({"records": []}).allowed,
            },
            "observability": scheduler.observability_snapshot(),
        }

    def scheduler_service(self) -> SchedulerService:
        return SchedulerService.build_default(rules_root=self.rules_root)

    def run_scheduler_cycle(self, *, count: int = 20, block_ms: int = 1_000) -> dict[str, Any]:
        scheduler = self.scheduler_service()
        scheduler.ensure_groups()
        return {
            "scheduler": scheduler.describe(),
            "results": scheduler.run_once(count=count, block_ms=block_ms),
            "observability": scheduler.observability_snapshot(),
        }

    def memory_runtime_service(self) -> MemoryRuntimeService:
        return MemoryRuntimeService.build_default(rules_root=self.rules_root)

    def run_memory_cycle(self, *, count: int = 20, block_ms: int = 1_000) -> dict[str, Any]:
        memory_runtime = self.memory_runtime_service()
        memory_runtime.ensure_group()
        return {
            "memory_runtime": memory_runtime.describe(),
            "results": memory_runtime.run_once(count=count, block_ms=block_ms),
        }

    def scheduler_health_report(self) -> dict[str, Any]:
        scheduler = self.scheduler_service()
        return {
            "scheduler": scheduler.describe(),
            "observability": scheduler.observability_snapshot(),
        }

    def dry_run_validation(self) -> dict[str, Any]:
        scheduler = self.scheduler_service()
        guardrail_report = scheduler.guardrails.dry_run_validation()
        memory = MemoryManager()
        memory_flush = memory.flush([])

        return {
            "runtime": "assistant_runtime",
            "phase": "guardrail_validation",
            "workspace_root": str(self.workspace_root),
            "guardrails_root": str(self.rules_root),
            "scheduler": scheduler.describe(),
            "guardrails": guardrail_report,
            "memory": {
                "layers": memory.memory_layers(),
                "flush_rules": memory_flush["rules"],
                "no_raw_conversation_storage": "never_store_raw_conversations"
                in cast(list[str], memory_flush["rules"]),
            },
            "bootstrap_coherent": not guardrail_report["missing_rules"],
        }
