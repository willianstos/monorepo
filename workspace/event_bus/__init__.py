"""Redis Streams event bus for orchestration-safe agent communication."""

from .audit import AUDIT_PAYLOAD_FIELDS, build_audit_payload
from .bus import RedisStreamBus
from .consumers import AgentEventConsumer, ConsumerRegistration, DefaultEventHandlers
from .events import AgentEvent, EventSource, StreamEventRecord, SUPPORTED_EVENT_TYPES, validate_event_dict
from .streams import (
    AGENT_RESULT_STREAM,
    AGENT_STREAM_SUBSCRIPTIONS,
    AGENT_TASK_STREAM,
    ALL_STREAMS,
    CI_EVENT_STREAM,
    MEMORY_EVENT_STREAM,
    SCHEDULER_STREAMS,
    SYSTEM_EVENT_STREAM,
    StreamName,
)

__all__ = [
    "AGENT_RESULT_STREAM",
    "AGENT_STREAM_SUBSCRIPTIONS",
    "AGENT_TASK_STREAM",
    "ALL_STREAMS",
    "AUDIT_PAYLOAD_FIELDS",
    "AgentEvent",
    "AgentEventConsumer",
    "CI_EVENT_STREAM",
    "ConsumerRegistration",
    "DefaultEventHandlers",
    "EventSource",
    "MEMORY_EVENT_STREAM",
    "RedisStreamBus",
    "SCHEDULER_STREAMS",
    "SUPPORTED_EVENT_TYPES",
    "SYSTEM_EVENT_STREAM",
    "StreamEventRecord",
    "StreamName",
    "build_audit_payload",
    "validate_event_dict",
]
