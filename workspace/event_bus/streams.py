from __future__ import annotations

from typing import Literal

StreamName = Literal[
    "agent_tasks",
    "agent_results",
    "ci_events",
    "memory_events",
    "system_events",
]

AGENT_TASK_STREAM: StreamName = "agent_tasks"
AGENT_RESULT_STREAM: StreamName = "agent_results"
CI_EVENT_STREAM: StreamName = "ci_events"
MEMORY_EVENT_STREAM: StreamName = "memory_events"
SYSTEM_EVENT_STREAM: StreamName = "system_events"

ALL_STREAMS: tuple[StreamName, ...] = (
    AGENT_TASK_STREAM,
    AGENT_RESULT_STREAM,
    CI_EVENT_STREAM,
    MEMORY_EVENT_STREAM,
    SYSTEM_EVENT_STREAM,
)

SCHEDULER_STREAMS: tuple[StreamName, ...] = (
    AGENT_TASK_STREAM,
    AGENT_RESULT_STREAM,
    CI_EVENT_STREAM,
    SYSTEM_EVENT_STREAM,
)

AGENT_STREAM_SUBSCRIPTIONS: dict[str, tuple[StreamName, ...]] = {
    "planner": (AGENT_TASK_STREAM, SYSTEM_EVENT_STREAM),
    "coder": (AGENT_TASK_STREAM, SYSTEM_EVENT_STREAM),
    "tester": (AGENT_TASK_STREAM, SYSTEM_EVENT_STREAM),
    "reviewer": (AGENT_TASK_STREAM, SYSTEM_EVENT_STREAM),
    "scheduler": SCHEDULER_STREAMS,
}
