from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from workspace.event_bus import RedisStreamBus
from workspace.scheduler.dag_builder import DAG_REDIS_KEYS, TaskGraph, TaskNode


@dataclass
class RedisDagStore:
    """Persist DAG and task state in Redis using granular graph/task keys."""

    bus: RedisStreamBus

    METRICS_KEY: str = "scheduler:metrics"
    THROUGHPUT_KEY: str = "scheduler:throughput"
    PROCESSED_EVENTS_KEY: str = "scheduler:processed_events"

    def describe(self) -> dict[str, Any]:
        return {
            "backend": "redis",
            "granular_keys": list(DAG_REDIS_KEYS),
            "opaque_dag_blob_allowed": False,
            "metrics_key": self.METRICS_KEY,
            "throughput_key": self.THROUGHPUT_KEY,
            "processed_events_key": self.PROCESSED_EVENTS_KEY,
        }

    def save_graph(self, graph: TaskGraph) -> None:
        client = self.bus.require_client()
        metadata = graph.to_metadata()
        client.hset(
            self.dag_key(graph.graph_id),
            mapping={
                "graph_id": metadata["graph_id"],
                "correlation_id": metadata["correlation_id"],
                "created_at": metadata["created_at"],
                "updated_at": metadata["updated_at"],
                "status": metadata["status"],
                "ci_status": metadata["ci_status"],
                "max_retry_limit": str(metadata["max_retry_limit"]),
                "retry_count": str(metadata["retry_count"]),
                "metadata": json.dumps(metadata["metadata"], sort_keys=True),
            },
        )
        client.delete(self.dag_tasks_key(graph.graph_id))
        if graph.tasks:
            client.sadd(self.dag_tasks_key(graph.graph_id), *graph.tasks.keys())
        for task in graph.tasks.values():
            self.save_task(task)

    def save_task(self, task: TaskNode) -> None:
        client = self.bus.require_client()
        client.hset(
            self.task_key(task.task_id),
            mapping={
                "task_id": task.task_id,
                "graph_id": task.graph_id,
                "task_type": task.task_type,
                "dependencies": json.dumps(list(task.dependencies)),
                "assigned_agent": task.assigned_agent,
                "status": task.status,
                "guardrail_policy": json.dumps(task.guardrail_policy, sort_keys=True),
                "retry_count": str(task.retry_count),
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            },
        )
        client.delete(self.taskdeps_key(task.task_id))
        if task.dependencies:
            client.sadd(self.taskdeps_key(task.task_id), *task.dependencies)
        client.set(self.taskstatus_key(task.task_id), task.status)
        client.sadd(self.dag_tasks_key(task.graph_id), task.task_id)

    def load_graph(self, graph_id: str) -> TaskGraph:
        client = self.bus.require_client()
        raw = client.hgetall(self.dag_key(graph_id))
        if not raw:
            raise KeyError(f"Graph '{graph_id}' was not found in Redis.")

        task_ids = sorted(str(task_id) for task_id in client.smembers(self.dag_tasks_key(graph_id)))
        tasks = {task_id: self.load_task(task_id) for task_id in task_ids}
        metadata = self._parse_json(raw.get("metadata"), default={})
        return TaskGraph.from_dict(
            {
                "graph_id": raw["graph_id"],
                "correlation_id": raw["correlation_id"],
                "created_at": raw["created_at"],
                "updated_at": raw["updated_at"],
                "status": raw["status"],
                "ci_status": raw["ci_status"],
                "max_retry_limit": int(raw["max_retry_limit"]),
                "retry_count": int(raw.get("retry_count", "0")),
                "metadata": metadata,
            },
            tasks=tasks,
        )

    def load_task(self, task_id: str) -> TaskNode:
        client = self.bus.require_client()
        raw = client.hgetall(self.task_key(task_id))
        if not raw:
            raise KeyError(f"Task '{task_id}' was not found in Redis.")

        dependencies = tuple(self._parse_json(raw.get("dependencies"), default=[]))
        if not dependencies:
            dependencies = tuple(
                str(dependency) for dependency in sorted(client.smembers(self.taskdeps_key(task_id)))
            )

        status = client.get(self.taskstatus_key(task_id)) or raw.get("status", "pending")
        return TaskNode(
            task_id=raw["task_id"],
            graph_id=raw["graph_id"],
            task_type=raw["task_type"],
            dependencies=tuple(str(dependency) for dependency in dependencies),
            assigned_agent=raw["assigned_agent"],  # type: ignore[arg-type]
            status=str(status),  # type: ignore[arg-type]
            guardrail_policy=self._parse_json(raw.get("guardrail_policy"), default={}),
            retry_count=int(raw.get("retry_count", "0")),
            created_at=raw["created_at"],
            updated_at=raw["updated_at"],
        )

    def update_task_status(self, task_id: str, status: str) -> TaskNode:
        task = self.load_task(task_id)
        updated_task = TaskNode(
            task_id=task.task_id,
            graph_id=task.graph_id,
            task_type=task.task_type,
            dependencies=task.dependencies,
            assigned_agent=task.assigned_agent,
            status=status,  # type: ignore[arg-type]
            guardrail_policy=task.guardrail_policy,
            retry_count=task.retry_count,
            created_at=task.created_at,
            updated_at=self.utcnow(),
        )
        self.save_task(updated_task)
        return updated_task

    def update_graph_ci_status(self, graph_id: str, ci_status: str) -> None:
        client = self.bus.require_client()
        client.hset(
            self.dag_key(graph_id),
            mapping={"ci_status": ci_status, "updated_at": self.utcnow()},
        )

    def increment_graph_retry(self, graph_id: str) -> int:
        client = self.bus.require_client()
        retry_count = int(client.hincrby(self.dag_key(graph_id), "retry_count", 1))
        client.hset(self.dag_key(graph_id), mapping={"updated_at": self.utcnow()})
        self.increment_metric("retries")
        return retry_count

    def increment_task_retry(self, task_id: str) -> int:
        client = self.bus.require_client()
        retry_count = int(client.hincrby(self.task_key(task_id), "retry_count", 1))
        client.hset(self.task_key(task_id), mapping={"updated_at": self.utcnow()})
        self.increment_metric("retries")
        return retry_count

    def append_task_dependency(self, task_id: str, dependency_id: str) -> None:
        task = self.load_task(task_id)
        if dependency_id in task.dependencies:
            return
        updated_dependencies = tuple([*task.dependencies, dependency_id])
        updated_task = TaskNode(
            task_id=task.task_id,
            graph_id=task.graph_id,
            task_type=task.task_type,
            dependencies=updated_dependencies,
            assigned_agent=task.assigned_agent,
            status=task.status,
            guardrail_policy=task.guardrail_policy,
            retry_count=task.retry_count,
            created_at=task.created_at,
            updated_at=self.utcnow(),
        )
        self.save_task(updated_task)

    def set_task_payload_field(self, task_id: str, key: str, value: Any) -> TaskNode:
        client = self.bus.require_client()
        serialized = value
        if isinstance(value, (dict, list, tuple)):
            serialized = json.dumps(value, sort_keys=True)
        elif isinstance(value, bool):
            serialized = json.dumps(value)
        elif value is None:
            serialized = ""

        client.hset(
            self.task_key(task_id),
            mapping={key: str(serialized), "updated_at": self.utcnow()},
        )
        if key == "status":
            client.set(self.taskstatus_key(task_id), str(value))
        return self.load_task(task_id)

    def find_graph_id_for_task(self, task_id: str) -> str:
        client = self.bus.require_client()
        raw = client.hgetall(self.task_key(task_id))
        if not raw:
            raise KeyError(f"Task '{task_id}' was not found in Redis.")
        return str(raw["graph_id"])

    def record_dead_letter(self, graph_id: str, task_id: str, reason: str) -> None:
        client = self.bus.require_client()
        client.rpush(
            self.dead_letter_key(graph_id),
            json.dumps(
                {
                    "graph_id": graph_id,
                    "task_id": task_id,
                    "reason": reason,
                    "recorded_at": self.utcnow(),
                },
                sort_keys=True,
            ),
        )
        self.increment_metric("dead_letters")

    def set_graph_status(self, graph_id: str, status: str) -> None:
        client = self.bus.require_client()
        client.hset(
            self.dag_key(graph_id),
            mapping={"status": status, "updated_at": self.utcnow()},
        )

    def set_graph_metadata_field(self, graph_id: str, key: str, value: Any) -> None:
        graph = self.load_graph(graph_id)
        metadata = dict(graph.metadata)
        metadata[key] = value
        client = self.bus.require_client()
        client.hset(
            self.dag_key(graph_id),
            mapping={"metadata": json.dumps(metadata, sort_keys=True), "updated_at": self.utcnow()},
        )

    def update_graph_metadata(self, graph_id: str, updates: dict[str, Any]) -> None:
        graph = self.load_graph(graph_id)
        metadata = dict(graph.metadata)
        metadata.update(updates)
        client = self.bus.require_client()
        client.hset(
            self.dag_key(graph_id),
            mapping={"metadata": json.dumps(metadata, sort_keys=True), "updated_at": self.utcnow()},
        )

    def increment_metric(self, metric: str, amount: int = 1) -> int:
        client = self.bus.require_client()
        return int(client.hincrby(self.METRICS_KEY, metric, amount))

    def increment_throughput(self, stage: str, task_type: str, amount: int = 1) -> int:
        client = self.bus.require_client()
        field = f"{stage}:{task_type}"
        return int(client.hincrby(self.THROUGHPUT_KEY, field, amount))

    def load_metrics_snapshot(self) -> dict[str, Any]:
        client = self.bus.require_client()
        metrics = {key: int(value) for key, value in client.hgetall(self.METRICS_KEY).items()}
        throughput: dict[str, dict[str, int]] = {}
        for field, value in client.hgetall(self.THROUGHPUT_KEY).items():
            stage, _, task_type = str(field).partition(":")
            throughput.setdefault(stage, {})[task_type] = int(value)
        return {"metrics": metrics, "throughput": throughput}

    def mark_event_processed(self, event_id: str) -> int:
        client = self.bus.require_client()
        return int(client.sadd(self.PROCESSED_EVENTS_KEY, event_id))

    def has_processed_event(self, event_id: str) -> bool:
        client = self.bus.require_client()
        if hasattr(client, "sismember"):
            return bool(client.sismember(self.PROCESSED_EVENTS_KEY, event_id))
        return event_id in {str(value) for value in client.smembers(self.PROCESSED_EVENTS_KEY)}

    def processed_event_count(self) -> int:
        client = self.bus.require_client()
        if hasattr(client, "scard"):
            return int(client.scard(self.PROCESSED_EVENTS_KEY))
        return len(client.smembers(self.PROCESSED_EVENTS_KEY))

    def dead_letter_key(self, graph_id: str) -> str:
        return f"dead_letter:{graph_id}"

    def dag_key(self, graph_id: str) -> str:
        return f"dag:{graph_id}"

    def dag_tasks_key(self, graph_id: str) -> str:
        return f"dag_tasks:{graph_id}"

    def task_key(self, task_id: str) -> str:
        return f"task:{task_id}"

    def taskdeps_key(self, task_id: str) -> str:
        return f"taskdeps:{task_id}"

    def taskstatus_key(self, task_id: str) -> str:
        return f"taskstatus:{task_id}"

    @staticmethod
    def _parse_json(raw_value: Any, *, default: Any) -> Any:
        if raw_value in (None, ""):
            return default
        if isinstance(raw_value, (dict, list)):
            return raw_value
        return json.loads(str(raw_value))

    @staticmethod
    def utcnow() -> str:
        return datetime.now(timezone.utc).isoformat()
