from __future__ import annotations

from typing import Any

from .events import AgentEvent

AUDIT_PAYLOAD_FIELDS: tuple[str, ...] = (
    "event_id",
    "correlation_id",
    "graph_id",
    "task_id",
    "source",
    "task_type",
    "previous_status",
    "next_status",
    "reason",
    "category",
    "result",
)


def build_audit_payload(
    event: AgentEvent,
    *,
    graph_id: str | None = None,
    task_id: str | None = None,
    task_type: str | None = None,
    previous_status: str | None = None,
    next_status: str | None = None,
    reason: str,
    category: str,
    result: str,
) -> dict[str, Any]:
    payload_task_type = event.payload.get("task_type")
    return {
        "event_id": event.event_id,
        "correlation_id": event.correlation_id,
        "graph_id": str(graph_id or event.payload.get("graph_id") or ""),
        "task_id": str(task_id or event.payload.get("task_id") or ""),
        "source": event.source,
        "task_type": str(task_type or payload_task_type or ""),
        "previous_status": previous_status or "",
        "next_status": next_status or "",
        "reason": reason,
        "category": category,
        "result": result,
    }
