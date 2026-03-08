from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from workspace.event_bus import (
    AGENT_TASK_STREAM,
    MEMORY_EVENT_STREAM,
    SYSTEM_EVENT_STREAM,
    AgentEvent,
)
from workspace.memory import MemoryRuntimeService
from workspace.scheduler import SchedulerService


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json_text(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True)


@dataclass(frozen=True)
class MCPToolDefinition:
    name: str
    title: str
    description: str
    input_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class SchedulerMCPAdapter:
    scheduler: SchedulerService

    @classmethod
    def build_default(cls) -> "SchedulerMCPAdapter":
        return cls(scheduler=SchedulerService.build_default(rules_root=_repo_root() / "guardrails"))

    def tool_definitions(self) -> list[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                name="scheduler_get_health",
                title="Scheduler Health",
                description="Return audit-safe scheduler health and operator signals.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="scheduler_get_graph_state",
                title="Graph State",
                description="Return graph metadata, task state, and dead-letter state for one graph.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string", "description": "Redis-backed graph identifier."},
                    },
                    "required": ["graph_id"],
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="scheduler_get_task_state",
                title="Task State",
                description="Return audit-safe state for one task.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task identifier."},
                    },
                    "required": ["task_id"],
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="scheduler_list_audit_events",
                title="Audit Events",
                description="Return recent audit_log or system_alert events from system_events.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "event_type": {
                            "type": "string",
                            "enum": ["audit_log", "system_alert"],
                            "default": "audit_log",
                        },
                        "graph_id": {"type": "string"},
                        "category": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                    },
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="scheduler_request_issue",
                title="Request Issue",
                description="Queue an issue_created event through the governed scheduler entrypoint.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "project_name": {"type": "string"},
                        "objective": {"type": "string"},
                        "correlation_id": {"type": "string"},
                    },
                    "required": ["graph_id", "project_name", "objective"],
                    "additionalProperties": False,
                },
            ),
        ]

    def supports_tool(self, name: str) -> bool:
        return any(tool.name == name for tool in self.tool_definitions())

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        if name == "scheduler_get_health":
            return self._scheduler_health_report()
        if name == "scheduler_get_graph_state":
            return self._graph_state(graph_id=self._require_non_empty(args, "graph_id"))
        if name == "scheduler_get_task_state":
            return self._task_state(task_id=self._require_non_empty(args, "task_id"))
        if name == "scheduler_list_audit_events":
            return self._audit_events(
                event_type=str(args.get("event_type") or "audit_log"),
                graph_id=self._optional_string(args, "graph_id"),
                category=self._optional_string(args, "category"),
                limit=self._coerce_limit(args.get("limit", 20)),
            )
        if name == "scheduler_request_issue":
            return self._request_issue(
                graph_id=self._require_non_empty(args, "graph_id"),
                project_name=self._require_non_empty(args, "project_name"),
                objective=self._require_non_empty(args, "objective"),
                correlation_id=self._optional_string(args, "correlation_id") or str(uuid4()),
            )
        raise KeyError(f"Unsupported scheduler MCP tool '{name}'.")

    def _scheduler_health_report(self) -> dict[str, Any]:
        observability = self.scheduler.observability_snapshot()
        metrics = dict(observability.get("metrics", {}))
        throughput = dict(observability.get("throughput", {}))
        created_total = sum(dict(throughput.get("created", {})).values())
        completed_total = sum(dict(throughput.get("completed", {})).values())
        cancelled_total = sum(dict(throughput.get("cancelled", {})).values())
        backlog_estimate = max(created_total - completed_total - cancelled_total, 0)
        dead_letters = int(metrics.get("dead_letters", 0))
        blocked_tasks = int(metrics.get("tasks_blocked", 0))
        merge_blocks = int(metrics.get("merge_blocks", 0))
        ci_failures = int(metrics.get("ci_failures", 0))
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
            operator_hints.append("Redis is unreachable from the scheduler.")
        if backlog_estimate > 0:
            operator_hints.append("Backlog is non-zero.")
        if dead_letters > 0:
            operator_hints.append("Dead-letter records exist.")
        if merge_blocks > 0:
            operator_hints.append("Merge blocks have been recorded.")
        if ci_failures > 0:
            operator_hints.append("CI failures were recorded.")
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
            "scheduler": self.scheduler.describe(),
            "observability": observability,
        }

    def _graph_state(self, *, graph_id: str) -> dict[str, Any]:
        graph = self.scheduler.store.load_graph(graph_id)
        client = self.scheduler.bus.require_client()
        dead_letters = [
            json.loads(item) for item in client.lrange(self.scheduler.store.dead_letter_key(graph_id), 0, -1)
        ]
        tasks = [
            {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "assigned_agent": task.assigned_agent,
                "status": task.status,
                "dependencies": list(task.dependencies),
                "retry_count": task.retry_count,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            }
            for task in sorted(graph.tasks.values(), key=lambda item: item.task_id)
        ]
        blocked_tasks = [task["task_id"] for task in tasks if task["status"] == "blocked"]
        retrying_tasks = [
            task["task_id"] for task in tasks if int(cast(int | str, task["retry_count"])) > 0
        ]

        return {
            "graph_id": graph.graph_id,
            "status": graph.status,
            "ci_status": graph.ci_status,
            "retry_count": graph.retry_count,
            "max_retry_limit": graph.max_retry_limit,
            "metadata": graph.metadata,
            "task_counts": self._count_task_statuses(tasks),
            "blocked_tasks": blocked_tasks,
            "retrying_tasks": retrying_tasks,
            "dead_letters": dead_letters,
            "tasks": tasks,
        }

    def _task_state(self, *, task_id: str) -> dict[str, Any]:
        task = self.scheduler.store.load_task(task_id)
        return {
            "task_id": task.task_id,
            "graph_id": task.graph_id,
            "task_type": task.task_type,
            "assigned_agent": task.assigned_agent,
            "status": task.status,
            "dependencies": list(task.dependencies),
            "guardrail_policy": task.guardrail_policy,
            "retry_count": task.retry_count,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    def _audit_events(
        self,
        *,
        event_type: str,
        graph_id: str | None,
        category: str | None,
        limit: int,
    ) -> dict[str, Any]:
        if event_type not in {"audit_log", "system_alert"}:
            raise ValueError("scheduler_list_audit_events only exposes 'audit_log' or 'system_alert'.")

        events = [
            event
            for event in self._stream_events(SYSTEM_EVENT_STREAM, limit=limit)
            if event.event_type == event_type
        ]
        if graph_id is not None:
            events = [event for event in events if event.payload.get("graph_id") == graph_id]
        if category is not None:
            events = [event for event in events if event.payload.get("category") == category]

        return {
            "stream": SYSTEM_EVENT_STREAM,
            "event_type": event_type,
            "graph_id": graph_id,
            "category": category,
            "events": [event.to_event_dict() for event in events[:limit]],
        }

    def _request_issue(
        self,
        *,
        graph_id: str,
        project_name: str,
        objective: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        event = AgentEvent.create(
            event_type="issue_created",
            source="system",
            correlation_id=correlation_id,
            payload={
                "graph_id": graph_id,
                "task_id": graph_id,
                "project_name": project_name,
                "objective": objective,
                "requested_via": "mcp",
            },
        )
        redis_id = self.scheduler.bus.publish(AGENT_TASK_STREAM, event)
        return {
            "status": "queued",
            "stream": AGENT_TASK_STREAM,
            "redis_id": redis_id,
            "event": event.to_event_dict(),
            "note": "Scheduler processing remains asynchronous and governed by Redis Streams.",
        }

    def _stream_events(self, stream: str, *, limit: int) -> list[AgentEvent]:
        client = self.scheduler.bus.require_client()
        if hasattr(client, "xrevrange"):
            raw_records = client.xrevrange(stream, max="+", min="-", count=limit)
            return [AgentEvent.from_dict(fields) for _, fields in raw_records]
        if hasattr(client, "xrange"):
            raw_records = client.xrange(stream, min="-", max="+", count=limit)
            return [AgentEvent.from_dict(fields) for _, fields in raw_records][-limit:]
        stream_records = list(client.streams.get(stream, []))[-limit:]  # type: ignore[attr-defined]
        return [AgentEvent.from_dict(fields) for _, fields in reversed(stream_records)]

    @staticmethod
    def _count_task_statuses(tasks: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for task in tasks:
            status = str(task["status"])
            counts[status] = counts.get(status, 0) + 1
        return counts

    @staticmethod
    def _coerce_limit(raw_value: Any) -> int:
        limit = int(raw_value)
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100.")
        return limit

    @staticmethod
    def _require_non_empty(arguments: dict[str, Any], key: str) -> str:
        value = str(arguments.get(key, "")).strip()
        if not value:
            raise ValueError(f"'{key}' is required.")
        return value

    @staticmethod
    def _optional_string(arguments: dict[str, Any], key: str) -> str | None:
        value = arguments.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None


@dataclass
class MemoryMCPAdapter:
    memory_runtime: MemoryRuntimeService

    @classmethod
    def build_default(cls) -> "MemoryMCPAdapter":
        return cls(memory_runtime=MemoryRuntimeService.build_default(rules_root=_repo_root() / "guardrails"))

    def tool_definitions(self) -> list[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                name="memory_get_project_records",
                title="Project Memory",
                description="Return distilled runtime memory records for one project.",
                input_schema={
                    "type": "object",
                    "properties": {"project_name": {"type": "string"}},
                    "required": ["project_name"],
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="memory_get_graph_records",
                title="Graph Memory",
                description="Return distilled runtime memory records for one graph.",
                input_schema={
                    "type": "object",
                    "properties": {"graph_id": {"type": "string"}},
                    "required": ["graph_id"],
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="memory_get_task_records",
                title="Task Memory",
                description="Return distilled runtime memory records for one task.",
                input_schema={
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="memory_submit_records",
                title="Submit Memory",
                description="Queue a structured memory_write_requested event after preflight validation.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string"},
                        "graph_id": {"type": "string"},
                        "task_id": {"type": "string"},
                        "records": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "memory_type": {
                                        "type": "string",
                                        "enum": ["learning", "decision", "architecture", "bug", "improvement"],
                                    },
                                    "topic": {"type": "string"},
                                    "summary": {"type": "string"},
                                    "confidence": {"type": "number"},
                                    "tags": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["memory_type", "topic", "summary", "confidence", "tags"],
                            },
                        },
                        "correlation_id": {"type": "string"},
                    },
                    "required": ["project_name", "graph_id", "task_id", "records"],
                    "additionalProperties": False,
                },
            ),
        ]

    def supports_tool(self, name: str) -> bool:
        return any(tool.name == name for tool in self.tool_definitions())

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        if name == "memory_get_project_records":
            return self._load_records(project_name=self._require_non_empty(args, "project_name"))
        if name == "memory_get_graph_records":
            return self._load_records(graph_id=self._require_non_empty(args, "graph_id"))
        if name == "memory_get_task_records":
            return self._load_records(task_id=self._require_non_empty(args, "task_id"))
        if name == "memory_submit_records":
            return self._submit_records(arguments=args)
        raise KeyError(f"Unsupported memory MCP tool '{name}'.")

    def _load_records(
        self,
        *,
        project_name: str | None = None,
        graph_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        records = self.memory_runtime.manager.load_runtime_records(
            self.memory_runtime.bus.require_client(),
            project_name=project_name,
            graph_id=graph_id,
            task_id=task_id,
        )
        return {
            "records": records,
            "record_count": len(records),
            "scope": {
                "project_name": project_name,
                "graph_id": graph_id,
                "task_id": task_id,
            },
        }

    def _submit_records(self, *, arguments: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "graph_id": self._require_non_empty(arguments, "graph_id"),
            "task_id": self._require_non_empty(arguments, "task_id"),
            "project_name": self._require_non_empty(arguments, "project_name"),
            "records": arguments.get("records", []),
            "requested_via": "mcp",
        }
        for raw_field in ("conversation", "conversations", "messages", "raw_conversation", "raw_messages", "transcript"):
            if raw_field in arguments:
                payload[raw_field] = arguments[raw_field]

        decision = self.memory_runtime.guardrails.validate_memory_payload(payload)
        if not decision.allowed:
            return {
                "status": "rejected",
                "published": False,
                "violations": decision.to_dict()["violations"],
            }

        correlation_id = str(arguments.get("correlation_id") or uuid4())
        event = AgentEvent.create(
            event_type="memory_write_requested",
            source="system",
            correlation_id=correlation_id,
            payload=payload,
        )
        redis_id = self.memory_runtime.bus.publish(MEMORY_EVENT_STREAM, event)
        return {
            "status": "queued",
            "published": True,
            "stream": MEMORY_EVENT_STREAM,
            "redis_id": redis_id,
            "event": event.to_event_dict(),
            "note": "Memory persistence remains asynchronous and governed by memory runtime validation.",
        }

    @staticmethod
    def _require_non_empty(arguments: dict[str, Any], key: str) -> str:
        value = str(arguments.get(key, "")).strip()
        if not value:
            raise ValueError(f"'{key}' is required.")
        return value


def tool_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": _json_text(payload)}],
        "isError": is_error,
    }
