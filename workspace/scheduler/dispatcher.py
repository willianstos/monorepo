from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workspace.event_bus import AGENT_TASK_STREAM, SYSTEM_EVENT_STREAM, AgentEvent, RedisStreamBus
from workspace.scheduler.dag_builder import TaskNode
from workspace.scheduler.dag_store import RedisDagStore
from workspace.scheduler.guardrail_enforcer import GuardrailEnforcer


@dataclass
class TaskDispatcher:
    """Publish ready tasks to the appropriate Redis Streams without direct agent calls."""

    bus: RedisStreamBus
    store: RedisDagStore
    guardrails: GuardrailEnforcer

    def describe(self) -> dict[str, Any]:
        return {
            "dispatch_streams": [AGENT_TASK_STREAM, SYSTEM_EVENT_STREAM],
            "dispatch_mode": "publish_events_only",
            "direct_agent_calls": False,
        }

    def dispatch_ready_tasks(self, graph_id: str) -> list[dict[str, Any]]:
        graph = self.store.load_graph(graph_id)
        ready_tasks = sorted(
            (task for task in graph.tasks.values() if task.status == "ready"),
            key=lambda task: (task.created_at, task.task_id),
        )

        dispatched: list[dict[str, Any]] = []
        for task in ready_tasks:
            decision = self.guardrails.validate_dispatch(task, graph)
            if not decision.allowed:
                dispatched.append(
                    {
                        "task_id": task.task_id,
                        "task_type": task.task_type,
                        "assigned_agent": task.assigned_agent,
                        "graph_id": graph_id,
                        "from_status": task.status,
                        "to_status": "blocked",
                        "dispatched": False,
                        "violations": decision.to_dict()["violations"],
                    }
                )
                continue

            if task.assigned_agent == "system":
                event = self.build_system_task_event(task, graph.correlation_id)
                stream = SYSTEM_EVENT_STREAM
            else:
                event = self.build_agent_task_event(task, graph.correlation_id)
                stream = AGENT_TASK_STREAM

            redis_id = self.bus.publish(stream, event)
            dispatched.append(
                {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "assigned_agent": task.assigned_agent,
                    "graph_id": graph_id,
                    "from_status": task.status,
                    "to_status": "running",
                    "stream": stream,
                    "event_id": redis_id,
                    "event_type": event.event_type,
                    "dispatched": True,
                }
            )

        return dispatched

    def build_agent_task_event(self, task: TaskNode, correlation_id: str) -> AgentEvent:
        event_type = "task_created"
        if task.assigned_agent == "tester":
            event_type = "tests_requested"
        elif task.assigned_agent == "reviewer":
            event_type = "review_requested"

        return AgentEvent.create(
            event_type=event_type,
            source="scheduler",
            correlation_id=correlation_id,
            payload=task.to_dict(),
        )

    def build_system_task_event(self, task: TaskNode, correlation_id: str) -> AgentEvent:
        event_type = "system_alert"
        if task.task_type == "human_approval_gate":
            event_type = "human_approval_required"
        elif task.task_type == "merge_task":
            event_type = "merge_requested"

        return AgentEvent.create(
            event_type=event_type,
            source="scheduler",
            correlation_id=correlation_id,
            payload=task.to_dict(),
        )
