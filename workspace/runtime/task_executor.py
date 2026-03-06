from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from workspace.event_bus import ALL_STREAMS, AgentEvent
from workspace.memory.schemas import MemoryRecord
from workspace.providers.model_auditor import ModelInfrastructureAuditor
from workspace.providers.model_router import ModelRouter


@dataclass
class TaskExecutor:
    task_id: str
    project_name: str
    provider_profile: str
    agent_flow: tuple[str, ...]
    gateway_chat_endpoint: str = "http://localhost:4000/v1/chat/completions"
    event_bus_backend: str = "redis_streams"
    event_streams: tuple[str, ...] = ALL_STREAMS
    memory_flush_required: bool = True
    memory_retrieval_strategy: tuple[str, ...] = (
        "semantic_memory",
        "structured_memory",
        "recent_sessions",
    )

    def describe(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "project_name": self.project_name,
            "provider_profile": self.provider_profile,
            "agent_flow": list(self.agent_flow),
            "gateway_chat_endpoint": self.gateway_chat_endpoint,
            "event_bus_backend": self.event_bus_backend,
            "event_streams": list(self.event_streams),
            "memory_flush_required": self.memory_flush_required,
            "memory_retrieval_strategy": list(self.memory_retrieval_strategy),
        }

    def prepare_model_route(self, objective: str) -> dict[str, Any]:
        auditor = ModelInfrastructureAuditor()
        router = ModelRouter(auditor=auditor)
        route = router.route_task(objective)
        audit = auditor.audit(objective)
        return {
            "audit": audit,
            "route": {
                "provider": route.provider,
                "model": route.model,
                "backend_type": route.backend_type,
                "transport": route.transport,
                "target": route.target,
            },
            "gateway_chat_endpoint": self.gateway_chat_endpoint,
        }

    def prepare_event_bus_bindings(self) -> dict[str, Any]:
        return {
            "backend": self.event_bus_backend,
            "streams": list(self.event_streams),
            "publish_only_handoffs": True,
            "acknowledgement_required": True,
        }

    def prepare_gateway_request(self, objective: str) -> dict[str, Any]:
        return {
            "url": self.gateway_chat_endpoint,
            "payload": {
                "model": "auto",
                "messages": [{"role": "user", "content": objective}],
                "metadata": {"task_description": objective},
            },
        }

    def prepare_task_event(self, objective: str, *, agent: str = "planner") -> dict[str, Any]:
        event = AgentEvent.create(
            event_type="issue_created",
            source=agent,
            correlation_id=self._correlation_id(),
            payload={
                "graph_id": self.task_id,
                "task_id": self.task_id,
                "project_name": self.project_name,
                "objective": objective,
                "agent_flow": list(self.agent_flow),
            },
        )
        return {"stream": "agent_tasks", "event": event.to_event_dict()}

    def prepare_task_graph_event(self, nodes: list[dict[str, Any]], *, agent: str = "planner") -> dict[str, Any]:
        event = AgentEvent.create(
            event_type="task_graph_created",
            source=agent,
            correlation_id=self._correlation_id(),
            payload={
                "graph_id": self.task_id,
                "tasks": nodes,
                "project_name": self.project_name,
            },
        )
        return {"stream": "system_events", "event": event.to_event_dict()}

    def prepare_result_event(
        self,
        *,
        agent: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = AgentEvent.create(
            event_type=event_type,
            source=agent,
            correlation_id=self._correlation_id(),
            payload={
                "graph_id": self.task_id,
                "task_id": self.task_id,
                "project_name": self.project_name,
                **(payload or {}),
            },
        )
        return {"stream": "agent_results", "event": event.to_event_dict()}

    def prepare_memory_flush(self) -> dict[str, Any]:
        return {
            "required": self.memory_flush_required,
            "flush_targets": [
                "key_decisions",
                "important_facts",
                "architecture_updates",
                "bugs_discovered",
                "fixes_implemented",
                "lessons_learned",
                "performance_insights",
            ],
        }

    def prepare_memory_event(self, records: list[MemoryRecord] | None = None) -> dict[str, Any]:
        event = AgentEvent.create(
            event_type="memory_write_requested",
            source="system",
            correlation_id=self._correlation_id(),
            payload={
                "graph_id": self.task_id,
                "task_id": self.task_id,
                "project_name": self.project_name,
                "records": records or [],
            },
        )
        return {"stream": "memory_events", "event": event.to_event_dict()}

    def prepare_system_event(self, event_type: str, *, agent: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = AgentEvent.create(
            event_type=event_type,
            source=agent,
            correlation_id=self._correlation_id(),
            payload={
                "graph_id": self.task_id,
                "task_id": self.task_id,
                "project_name": self.project_name,
                **payload,
            },
        )
        return {"stream": "system_events", "event": event.to_event_dict()}

    def prepare_ci_event(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = AgentEvent.create(
            event_type=event_type,
            source="ci",
            correlation_id=self._correlation_id(),
            payload={
                "graph_id": self.task_id,
                "task_id": self.task_id,
                "project_name": self.project_name,
                **(payload or {}),
            },
        )
        return {"stream": "ci_events", "event": event.to_event_dict()}

    def execute(self) -> Any:
        raise NotImplementedError(
            "Task execution through LangGraph and Redis Streams is intentionally not implemented yet."
        )

    def _correlation_id(self) -> str:
        try:
            return str(UUID(self.task_id))
        except ValueError:
            return str(uuid5(NAMESPACE_URL, f"task:{self.task_id}"))
