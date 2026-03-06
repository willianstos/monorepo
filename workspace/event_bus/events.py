from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping
from uuid import UUID, uuid4

from .streams import ALL_STREAMS, StreamName

EventSource = Literal["planner", "coder", "tester", "reviewer", "scheduler", "ci", "system"]

SUPPORTED_EVENT_TYPES: tuple[str, ...] = (
    "issue_created",
    "task_graph_created",
    "task_created",
    "task_started",
    "task_completed",
    "task_failed",
    "code_generated",
    "tests_requested",
    "review_requested",
    "ci_started",
    "ci_failed",
    "ci_passed",
    "coverage_failed",
    "security_failed",
    "human_approval_required",
    "merge_requested",
    "memory_write_requested",
    "system_alert",
    "audit_log",
)


@dataclass(frozen=True)
class AgentEvent:
    event_type: str
    event_id: str
    timestamp: str
    source: str
    correlation_id: str
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def agent(self) -> str:
        """Compatibility alias for older call sites."""

        return self.source

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        source: str | None = None,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        timestamp: str | None = None,
        event_id: str | None = None,
        agent: str | None = None,
    ) -> "AgentEvent":
        event = cls(
            event_type=event_type.strip(),
            event_id=event_id or str(uuid4()),
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            source=(source or agent or "system").strip(),
            correlation_id=correlation_id or str(uuid4()),
            payload=payload or {},
        )
        event.validate()
        return event

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentEvent":
        payload = data.get("payload", {})
        if isinstance(payload, str):
            payload = json.loads(payload)

        event = cls(
            event_type=str(data.get("event_type", "")).strip(),
            event_id=str(data.get("event_id", "")).strip(),
            timestamp=str(data.get("timestamp", "")).strip(),
            source=str(data.get("source", data.get("agent", ""))).strip(),
            correlation_id=str(data.get("correlation_id", "")).strip(),
            payload=dict(payload or {}),
        )
        event.validate()
        return event

    def validate(self) -> None:
        if not self.event_type:
            raise ValueError("event_type is required.")
        if not self.event_id:
            raise ValueError("event_id is required.")
        if not self.timestamp:
            raise ValueError("timestamp is required.")
        if not self.source:
            raise ValueError("source is required.")
        if not self.correlation_id:
            raise ValueError("correlation_id is required.")
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dictionary.")

        UUID(self.event_id)
        UUID(self.correlation_id)
        datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))

    def is_supported_type(self) -> bool:
        return self.event_type in SUPPORTED_EVENT_TYPES

    def to_event_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
        }

    def to_stream_fields(self) -> dict[str, str]:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "payload": json.dumps(self.payload, sort_keys=True),
        }


@dataclass(frozen=True)
class StreamEventRecord:
    stream: StreamName
    event_id: str
    event: AgentEvent

    @property
    def redis_id(self) -> str:
        return self.event_id


def validate_event_dict(data: Mapping[str, Any]) -> dict[str, Any]:
    return AgentEvent.from_dict(data).to_event_dict()


def validate_stream_name(stream: str) -> StreamName:
    if stream not in ALL_STREAMS:
        raise ValueError(f"Unsupported stream '{stream}'.")
    return stream  # type: ignore[return-value]
