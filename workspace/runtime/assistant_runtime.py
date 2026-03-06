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
        observability = scheduler.observability_snapshot()
        metrics = cast(dict[str, int], observability.get("metrics", {}))
        throughput = cast(dict[str, dict[str, int]], observability.get("throughput", {}))
        created_total = sum(throughput.get("created", {}).values())
        completed_total = sum(throughput.get("completed", {}).values())
        cancelled_total = sum(throughput.get("cancelled", {}).values())
        backlog_estimate = max(created_total - completed_total - cancelled_total, 0)
        dead_letters = metrics.get("dead_letters", 0)
        blocked_tasks = metrics.get("tasks_blocked", 0)
        merge_blocks = metrics.get("merge_blocks", 0)
        ci_failures = metrics.get("ci_failures", 0)
        connection_available = bool(observability.get("connection_available")) and not bool(
            observability.get("connection_error")
        )

        status = "healthy"
        if not connection_available:
            status = "unavailable"
        elif any(value > 0 for value in (dead_letters, blocked_tasks, merge_blocks, ci_failures, backlog_estimate)):
            status = "attention_required"

        operator_hints: list[str] = []
        if not connection_available:
            operator_hints.append("Redis is unreachable from the scheduler; run bootstrap/redis_diagnostics.py.")
        if backlog_estimate > 0:
            operator_hints.append("Backlog is non-zero; compare scheduler throughput created vs completed counts.")
        if dead_letters > 0:
            operator_hints.append("Dead-letter records exist; inspect dead_letter:* and matching audit_log events.")
        if merge_blocks > 0:
            operator_hints.append(
                "Merge blocks were recorded in this Redis history; confirm human approval metadata for the graph."
            )
        if ci_failures > 0:
            operator_hints.append("CI failures were recorded; inspect ci_events ordering and rerun_ci progression.")
        if not operator_hints:
            operator_hints.append("No blocking scheduler signals are currently visible.")

        return {
            "status": status,
            "summary": {
                "connection_available": connection_available,
                "processed_event_count": int(observability.get("processed_event_count", 0)),
                "created_total": created_total,
                "completed_total": completed_total,
                "cancelled_total": cancelled_total,
                "backlog_estimate": backlog_estimate,
                "dead_letters": dead_letters,
                "tasks_blocked": blocked_tasks,
                "merge_blocks": merge_blocks,
                "ci_failures": ci_failures,
            },
            "operator_hints": operator_hints,
            "scheduler": scheduler.describe(),
            "observability": observability,
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
