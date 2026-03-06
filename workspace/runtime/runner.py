from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from workspace.event_bus import AgentEventConsumer, RedisStreamBus, SCHEDULER_STREAMS, ALL_STREAMS
from workspace.gateway.router import GatewayRouter
from workspace.memory import MemoryManager, MemoryRuntimeService
from workspace.providers.model_auditor import ModelInfrastructureAuditor
from workspace.providers.model_router import ModelRouter
from workspace.scheduler import SchedulerService


@dataclass
class Runner:
    workspace_root: Path
    config_root: Path | None = None
    context_root: Path | None = None

    def __post_init__(self) -> None:
        if self.config_root is None:
            self.config_root = self.workspace_root / "config"
        if self.context_root is None:
            self.context_root = self.workspace_root.parent / ".context"

    def describe(self) -> dict[str, Any]:
        return {
            "workspace_root": str(self.workspace_root),
            "config_root": str(self.config_root),
            "context_root": str(self.context_root),
            "components": [
                "agents",
                "config",
                "gateway",
                "langgraph",
                "providers",
                "runtime",
                "scheduler",
                "tools",
                "memory",
                "event_bus",
            ],
            "bootstrap_order": [
                "langgraph_graph",
                "agents_configuration",
                "model_stack",
                "llm_gateway",
                "tools",
                "event_bus",
                "task_scheduler",
                "mcp_context",
                "memory_system",
            ],
        }

    def load_langgraph_graph(self) -> dict[str, Any]:
        graph_module = import_module("workspace.langgraph.graph")
        blueprint = graph_module.get_graph_blueprint()
        return {
            "module": "workspace.langgraph.graph",
            "blueprint_name": blueprint.name,
            "entrypoint": blueprint.entrypoint,
            "default_route": list(blueprint.default_route),
        }

    def load_agents_configuration(self) -> dict[str, Any]:
        config_root = self.config_root
        assert config_root is not None
        config_path = config_root / "agents.yaml"
        return {
            "path": str(config_path),
            "exists": config_path.exists(),
        }

    def load_model_stack(self) -> dict[str, Any]:
        auditor = ModelInfrastructureAuditor()
        router = ModelRouter(auditor=auditor)
        config_root = self.config_root
        assert config_root is not None
        config_path = config_root / "models.yaml"
        sample_route = router.route_task("Classify tool output and summarize logs")
        return {
            "path": str(config_path),
            "exists": config_path.exists(),
            "available_providers": ["local", "codex", "claude"],
            "local_first_for_helper_tasks": True,
            "escalation_threshold": auditor.escalation_threshold,
            "sample_route": {
                "provider": sample_route.provider,
                "model": sample_route.model,
                "backend_type": sample_route.backend_type,
                "transport": sample_route.transport,
            },
            "specializations": {
                "local": "bounded_low_risk_helper_only",
                "codex": "implementation_and_repository_edits",
                "claude": "planning_architecture_debugging_and_review",
            },
        }

    def load_llm_gateway(self) -> dict[str, Any]:
        router = GatewayRouter()
        return {
            "endpoint": "http://localhost:4000/v1/chat/completions",
            "health_endpoint": "http://localhost:4000/health",
            "router_module": "workspace.gateway.router",
            "server_module": "workspace.gateway.server",
            "providers": sorted(router._providers.keys()),
            "chat_completions_compatible": True,
        }

    def load_tools(self) -> dict[str, Any]:
        from workspace.tools import TOOL_REGISTRY

        config_root = self.config_root
        assert config_root is not None
        config_path = config_root / "tools.yaml"
        return {
            "path": str(config_path),
            "exists": config_path.exists(),
            "registry": sorted(TOOL_REGISTRY.keys()),
        }

    def load_event_bus(self) -> dict[str, Any]:
        bus = RedisStreamBus()
        planner_consumer = AgentEventConsumer.build_default(bus=bus, consumer_role="planner")

        connection_available = False
        connection_error: str | None = None
        try:
            connection_available = bus.ping()
        except Exception as exc:  # pragma: no cover - environment dependent
            connection_error = str(exc)

        return {
            "module": "workspace.event_bus.bus",
            "consumer_module": "workspace.event_bus.consumers",
            "backend": "redis_streams",
            "streams": list(ALL_STREAMS),
            "redis": {
                "host": bus.host,
                "port": bus.port,
                "db": bus.db,
                "connection_available": connection_available,
                "connection_error": connection_error,
            },
            "agent_communication_policy": "publish_subscribe_only",
            "acknowledgement_required": True,
            "sample_consumer_group": planner_consumer.group_name,
            "sample_subscriptions": list(planner_consumer.subscribed_streams()),
        }

    def load_task_scheduler(self) -> dict[str, Any]:
        scheduler = SchedulerService.build_default(rules_root=self.workspace_root.parent / "guardrails")
        return {
            "module": "workspace.scheduler.service",
            "backend": "task_dag_over_redis_streams",
            "consumer_group": scheduler.group_name,
            "consumer_name": scheduler.consumer_name,
            "subscribed_streams": list(SCHEDULER_STREAMS),
            "coordination_mode": "event_driven_only",
            "guardrails": {
                "coder_cannot_modify_tests": True,
                "tests_owned_by_tester": True,
                "review_owned_by_reviewer": True,
                "ci_is_authoritative": True,
                "direct_agent_calls_forbidden": True,
                "merge_requires_human_approval": True,
            },
        }

    def load_mcp_context(self) -> dict[str, Any]:
        context_root = self.context_root
        assert context_root is not None
        docs_root = context_root / "docs"
        agents_root = context_root / "agents"
        return {
            "path": str(context_root),
            "exists": context_root.exists(),
            "docs_root": str(docs_root),
            "docs_available": docs_root.exists(),
            "agents_root": str(agents_root),
            "agent_docs_available": agents_root.exists(),
        }

    def load_memory_system(self) -> dict[str, Any]:
        manager = MemoryManager()
        runtime_service = MemoryRuntimeService.build_default(rules_root=self.workspace_root.parent / "guardrails")
        config_root = self.config_root
        assert config_root is not None
        config_path = config_root / "memory.yaml"
        return {
            "path": str(config_path),
            "exists": config_path.exists(),
            "layers": manager.memory_layers(),
            "retrieval_order": list(manager.retrieval_order()),
            "runtime_write_path": runtime_service.describe(),
        }

    def bootstrap(self) -> dict[str, Any]:
        """Bootstrap the workspace architecture without executing the LangGraph runtime."""

        return {
            "langgraph_graph": self.load_langgraph_graph(),
            "agents_configuration": self.load_agents_configuration(),
            "model_stack": self.load_model_stack(),
            "llm_gateway": self.load_llm_gateway(),
            "tools": self.load_tools(),
            "event_bus": self.load_event_bus(),
            "task_scheduler": self.load_task_scheduler(),
            "mcp_context": self.load_mcp_context(),
            "memory_system": self.load_memory_system(),
        }
