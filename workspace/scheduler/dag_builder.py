from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, cast

from workspace.event_bus import AgentEvent

TaskStatus = Literal["pending", "ready", "running", "blocked", "failed", "completed", "cancelled"]
AssignedActor = Literal["planner", "coder", "tester", "reviewer", "system"]
TASK_STATUS_VALUES: tuple[TaskStatus, ...] = (
    "pending",
    "ready",
    "running",
    "blocked",
    "failed",
    "completed",
    "cancelled",
)
ASSIGNED_ACTOR_VALUES: tuple[AssignedActor, ...] = ("planner", "coder", "tester", "reviewer", "system")

TASK_NODE_FIELDS: tuple[str, ...] = (
    "task_id",
    "graph_id",
    "task_type",
    "dependencies",
    "assigned_agent",
    "status",
    "guardrail_policy",
    "retry_count",
    "created_at",
    "updated_at",
)

DAG_REDIS_KEYS: tuple[str, ...] = (
    "dag:{graph_id}",
    "dag_tasks:{graph_id}",
    "task:{task_id}",
    "taskdeps:{task_id}",
    "taskstatus:{task_id}",
)

DEFAULT_PIPELINE: tuple[str, ...] = (
    "plan_task",
    "implement_task",
    "test_task",
    "review_task",
    "human_approval_gate",
    "merge_task",
)

FIX_LOOP_PIPELINE: tuple[str, ...] = ("ci_failed", "fix_task", "rerun_ci", "ci_passed")

TASK_ASSIGNMENTS: dict[str, AssignedActor] = {
    "plan_task": "planner",
    "implement_task": "coder",
    "test_task": "tester",
    "review_task": "reviewer",
    "human_approval_gate": "system",
    "merge_task": "system",
    "fix_task": "coder",
    "rerun_ci": "system",
}


@dataclass(frozen=True)
class TaskNode:
    task_id: str
    graph_id: str
    task_type: str
    dependencies: tuple[str, ...]
    assigned_agent: AssignedActor
    status: TaskStatus
    guardrail_policy: dict[str, Any]
    retry_count: int
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "graph_id": self.graph_id,
            "task_type": self.task_type,
            "dependencies": list(self.dependencies),
            "assigned_agent": self.assigned_agent,
            "status": self.status,
            "guardrail_policy": self.guardrail_policy,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class TaskGraph:
    graph_id: str
    correlation_id: str
    created_at: str
    updated_at: str
    status: str
    ci_status: str
    max_retry_limit: int
    retry_count: int = 0
    tasks: dict[str, TaskNode] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "ci_status": self.ci_status,
            "max_retry_limit": self.max_retry_limit,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, tasks: dict[str, TaskNode]) -> "TaskGraph":
        return cls(
            graph_id=str(data["graph_id"]),
            correlation_id=str(data["correlation_id"]),
            created_at=str(data["created_at"]),
            updated_at=str(data["updated_at"]),
            status=str(data["status"]),
            ci_status=str(data["ci_status"]),
            max_retry_limit=int(data["max_retry_limit"]),
            retry_count=int(data.get("retry_count", 0)),
            tasks=tasks,
            metadata=dict(data.get("metadata", {})),
        )


class DagBuilder:
    """Build default orchestration DAGs using the repository's fixed contracts."""

    def describe(self) -> dict[str, Any]:
        return {
            "task_node_fields": list(TASK_NODE_FIELDS),
            "allowed_statuses": [
                "pending",
                "ready",
                "running",
                "blocked",
                "failed",
                "completed",
                "cancelled",
            ],
            "default_pipeline": list(DEFAULT_PIPELINE),
            "fix_loop_pipeline": list(FIX_LOOP_PIPELINE),
            "redis_keys": list(DAG_REDIS_KEYS),
        }

    def default_guardrail_policy(self, *, task_type: str, assigned_agent: AssignedActor) -> dict[str, Any]:
        return {
            "task_type": task_type,
            "assigned_agent": assigned_agent,
            "requires_ci_pass": task_type in {"review_task", "human_approval_gate", "merge_task"},
            "requires_human_approval": task_type in {"human_approval_gate", "merge_task"},
            "allow_test_modifications": assigned_agent == "tester",
            "allow_ci_modifications": False,
            "allow_direct_agent_calls": False,
            "allow_push_to_main": False,
        }

    def build_from_issue(self, event: AgentEvent, *, max_retry_limit: int = 2) -> TaskGraph:
        payload = dict(event.payload)
        graph_id = str(payload.get("graph_id") or event.correlation_id)
        created_at = event.timestamp
        tasks: dict[str, TaskNode] = {}
        previous_task_id: str | None = None

        for task_type in DEFAULT_PIPELINE:
            task_id = self.build_task_id(graph_id, task_type)
            dependencies = (previous_task_id,) if previous_task_id else ()
            assigned_agent = self.assigned_agent_for(task_type)
            tasks[task_id] = self.build_task_node(
                graph_id=graph_id,
                task_id=task_id,
                task_type=task_type,
                assigned_agent=assigned_agent,
                dependencies=dependencies,
                created_at=created_at,
                updated_at=created_at,
                status="ready" if not dependencies else "pending",
            )
            previous_task_id = task_id

        metadata = {
            key: value
            for key, value in payload.items()
            if key not in {"graph_id", "task_id", "tasks"}
        }
        metadata["source_event"] = event.event_type

        return TaskGraph(
            graph_id=graph_id,
            correlation_id=event.correlation_id,
            created_at=created_at,
            updated_at=created_at,
            status="active",
            ci_status="not_started",
            max_retry_limit=max_retry_limit,
            retry_count=0,
            tasks=tasks,
            metadata=metadata,
        )

    def build_from_task_graph(self, event: AgentEvent) -> TaskGraph:
        payload = dict(event.payload)
        graph_id = str(payload.get("graph_id") or event.correlation_id)
        created_at = event.timestamp
        nodes = list(payload.get("tasks", []))
        tasks: dict[str, TaskNode] = {}
        previous_task_id: str | None = None

        for index, raw_node in enumerate(nodes):
            task_type = str(raw_node.get("task_type") or raw_node.get("name") or f"task_{index + 1}")
            task_id = str(raw_node.get("task_id") or self.build_task_id(graph_id, task_type, suffix=index + 1))
            explicit_dependencies = raw_node.get("dependencies")
            dependencies: tuple[str, ...]
            if explicit_dependencies is None and previous_task_id:
                dependencies = (previous_task_id,)
            else:
                dependencies = tuple(str(dependency) for dependency in explicit_dependencies or ())

            assigned_agent = self.coerce_assigned_actor(
                raw_node.get("assigned_agent") or self.assigned_agent_for(task_type)
            )
            status = self.coerce_task_status(raw_node.get("status") or ("ready" if not dependencies else "pending"))
            guardrail_policy = dict(
                raw_node.get("guardrail_policy")
                or self.default_guardrail_policy(task_type=task_type, assigned_agent=assigned_agent)
            )

            tasks[task_id] = self.build_task_node(
                graph_id=graph_id,
                task_id=task_id,
                task_type=task_type,
                assigned_agent=assigned_agent,
                dependencies=dependencies,
                created_at=str(raw_node.get("created_at") or created_at),
                updated_at=str(raw_node.get("updated_at") or created_at),
                status=status,
                guardrail_policy=guardrail_policy,
                retry_count=int(raw_node.get("retry_count", 0)),
            )
            previous_task_id = task_id

        metadata = {
            key: value
            for key, value in payload.items()
            if key not in {"graph_id", "tasks", "status", "ci_status", "max_retry_limit", "retry_count"}
        }
        metadata["source_event"] = event.event_type

        return TaskGraph(
            graph_id=graph_id,
            correlation_id=event.correlation_id,
            created_at=created_at,
            updated_at=created_at,
            status=str(payload.get("status", "active")),
            ci_status=str(payload.get("ci_status", "not_started")),
            max_retry_limit=int(payload.get("max_retry_limit", 2)),
            retry_count=int(payload.get("retry_count", 0)),
            tasks=tasks,
            metadata=metadata,
        )

    def build_fix_loop(self, graph: TaskGraph, event: AgentEvent) -> tuple[TaskNode, TaskNode]:
        retry_sequence = max(1, graph.retry_count)
        timestamp = event.timestamp
        fix_task_id = self.build_task_id(graph.graph_id, "fix_task", suffix=retry_sequence)
        rerun_task_id = self.build_task_id(graph.graph_id, "rerun_ci", suffix=retry_sequence)

        fix_task = self.build_task_node(
            graph_id=graph.graph_id,
            task_id=fix_task_id,
            task_type="fix_task",
            assigned_agent="coder",
            dependencies=(),
            created_at=timestamp,
            updated_at=timestamp,
            status="ready",
            guardrail_policy={
                **self.default_guardrail_policy(task_type="fix_task", assigned_agent="coder"),
                "ci_failure_event": event.event_type,
                "retry_sequence": retry_sequence,
            },
        )
        rerun_task = self.build_task_node(
            graph_id=graph.graph_id,
            task_id=rerun_task_id,
            task_type="rerun_ci",
            assigned_agent="system",
            dependencies=(fix_task_id,),
            created_at=timestamp,
            updated_at=timestamp,
            status="pending",
            guardrail_policy={
                **self.default_guardrail_policy(task_type="rerun_ci", assigned_agent="system"),
                "requires_ci_pass": False,
                "requires_human_approval": False,
                "ci_failure_event": event.event_type,
                "retry_sequence": retry_sequence,
            },
        )
        return fix_task, rerun_task

    def build_task_node(
        self,
        *,
        graph_id: str,
        task_id: str,
        task_type: str,
        assigned_agent: AssignedActor,
        dependencies: tuple[str, ...],
        created_at: str | None = None,
        updated_at: str | None = None,
        status: TaskStatus = "pending",
        guardrail_policy: dict[str, Any] | None = None,
        retry_count: int = 0,
    ) -> TaskNode:
        timestamp = created_at or self.utcnow()
        return TaskNode(
            task_id=task_id,
            graph_id=graph_id,
            task_type=task_type,
            dependencies=dependencies,
            assigned_agent=assigned_agent,
            status=status,
            guardrail_policy=guardrail_policy
            or self.default_guardrail_policy(task_type=task_type, assigned_agent=assigned_agent),
            retry_count=retry_count,
            created_at=timestamp,
            updated_at=updated_at or timestamp,
        )

    def assigned_agent_for(self, task_type: str) -> AssignedActor:
        return TASK_ASSIGNMENTS.get(task_type, "system")

    @staticmethod
    def coerce_assigned_actor(raw_value: Any) -> AssignedActor:
        actor = str(raw_value).strip().lower()
        if actor not in ASSIGNED_ACTOR_VALUES:
            raise ValueError(f"Unsupported assigned_agent '{raw_value}'.")
        return cast(AssignedActor, actor)

    @staticmethod
    def coerce_task_status(raw_value: Any) -> TaskStatus:
        status = str(raw_value).strip().lower()
        if status not in TASK_STATUS_VALUES:
            raise ValueError(f"Unsupported task status '{raw_value}'.")
        return cast(TaskStatus, status)

    def build_task_id(self, graph_id: str, task_type: str, *, suffix: int | None = None) -> str:
        if suffix is None:
            return f"{graph_id}:{task_type}"
        return f"{graph_id}:{task_type}:{suffix}"

    @staticmethod
    def utcnow() -> str:
        return datetime.now(timezone.utc).isoformat()
