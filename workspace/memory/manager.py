from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from workspace.memory.schemas import MemoryRecord, MemoryType


@dataclass
class MemoryManager:
    working_backend: str = "redis"
    session_backend: str = "session_store"
    long_term_backend: str = "postgres_vector"

    RUNTIME_PROJECT_KEY_TEMPLATE: str = "memory:project:{project_name}:records"
    RUNTIME_GRAPH_KEY_TEMPLATE: str = "memory:graph:{graph_id}:records"
    RUNTIME_TASK_KEY_TEMPLATE: str = "memory:task:{task_id}:records"

    def memory_layers(self) -> dict[str, dict[str, str | list[str]]]:
        return {
            "working_memory": {
                "backend": self.working_backend,
                "purpose": "Temporary task state, agent state, and partial outputs.",
                "retention": "minutes_to_hours",
                "contents": ["current_tasks", "agent_state", "partial_outputs"],
            },
            "session_memory": {
                "backend": self.session_backend,
                "purpose": "Recent interaction continuity.",
                "retention": "hours_to_days",
                "contents": ["recent_tasks", "recent_decisions", "recent_outputs"],
            },
            "long_term_memory": {
                "backend": self.long_term_backend,
                "purpose": "Persistent knowledge with structured records and vector retrieval.",
                "retention": "persistent",
                "contents": [
                    "decisions",
                    "architecture_changes",
                    "experiment_results",
                    "project_knowledge",
                    "system_learnings",
                ],
            },
        }

    def build_record(
        self,
        memory_type: MemoryType,
        topic: str,
        summary: str,
        confidence: float,
        tags: list[str],
    ) -> MemoryRecord:
        return {
            "memory_type": memory_type,
            "topic": topic.strip(),
            "summary": summary.strip(),
            "confidence": max(0.0, min(confidence, 1.0)),
            "tags": sorted({tag.strip() for tag in tags if tag.strip()}),
        }

    def deduplicate(self, records: Iterable[MemoryRecord]) -> list[MemoryRecord]:
        unique: dict[tuple[str, str, str], MemoryRecord] = {}
        for record in records:
            key = (record["memory_type"], record["topic"], record["summary"])
            unique[key] = record
        return list(unique.values())

    def flush(self, records: Iterable[MemoryRecord]) -> dict[str, object]:
        distilled = self.deduplicate(records)
        return {
            "flush_required": bool(distilled),
            "records": distilled,
            "storage_targets": ["session_memory", "long_term_memory"],
            "rules": [
                "never_store_raw_conversations",
                "store_distilled_knowledge_only",
                "prefer_short_structured_summaries",
                "avoid_duplicates",
                "always_attach_tags",
            ],
        }

    def retrieval_order(self) -> tuple[str, ...]:
        return ("semantic_memory", "structured_memory", "recent_sessions")

    def runtime_keys(self, *, project_name: str, graph_id: str, task_id: str) -> dict[str, str]:
        return {
            "project": self.RUNTIME_PROJECT_KEY_TEMPLATE.format(project_name=project_name),
            "graph": self.RUNTIME_GRAPH_KEY_TEMPLATE.format(graph_id=graph_id),
            "task": self.RUNTIME_TASK_KEY_TEMPLATE.format(task_id=task_id),
        }

    def persist_runtime_records(
        self,
        client: Any,
        *,
        project_name: str,
        graph_id: str,
        task_id: str,
        records: Iterable[MemoryRecord],
    ) -> dict[str, Any]:
        distilled = self.deduplicate(records)
        keys = self.runtime_keys(project_name=project_name, graph_id=graph_id, task_id=task_id)
        serialized_records = [json.dumps(record, sort_keys=True) for record in distilled]

        if serialized_records:
            for key in keys.values():
                client.rpush(key, *serialized_records)

        return {
            "records_persisted": len(distilled),
            "keys": keys,
            "records": distilled,
        }

    def load_runtime_records(
        self,
        client: Any,
        *,
        project_name: str | None = None,
        graph_id: str | None = None,
        task_id: str | None = None,
    ) -> list[MemoryRecord]:
        if project_name is not None:
            key = self.RUNTIME_PROJECT_KEY_TEMPLATE.format(project_name=project_name)
        elif graph_id is not None:
            key = self.RUNTIME_GRAPH_KEY_TEMPLATE.format(graph_id=graph_id)
        elif task_id is not None:
            key = self.RUNTIME_TASK_KEY_TEMPLATE.format(task_id=task_id)
        else:
            raise ValueError("One of project_name, graph_id, or task_id is required.")

        values = client.lrange(key, 0, -1)
        return [json.loads(value) for value in values]
