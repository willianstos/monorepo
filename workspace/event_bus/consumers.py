from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from workspace.event_bus.bus import RedisStreamBus
from workspace.event_bus.events import AgentEvent, StreamEventRecord
from workspace.event_bus.streams import AGENT_STREAM_SUBSCRIPTIONS, ALL_STREAMS, StreamName

EventHandler = Callable[[StreamEventRecord], dict[str, Any] | None]


@dataclass(frozen=True)
class ConsumerRegistration:
    stream: StreamName
    handler: EventHandler
    event_types: tuple[str, ...] = ()

    def matches(self, event: AgentEvent) -> bool:
        return not self.event_types or event.event_type in self.event_types


class DefaultEventHandlers:
    @staticmethod
    def capture(record: StreamEventRecord) -> dict[str, Any]:
        return {
            "stream": record.stream,
            "redis_id": record.event_id,
            "event_type": record.event.event_type,
            "source": record.event.source,
            "correlation_id": record.event.correlation_id,
        }


@dataclass
class AgentEventConsumer:
    bus: RedisStreamBus
    group_name: str
    consumer_name: str
    subscriptions: tuple[ConsumerRegistration, ...]
    start_id: str = "0"

    def ensure_groups(self) -> None:
        self.bus.ensure_consumer_groups(self.subscribed_streams(), self.group_name, start_id=self.start_id)

    def poll_once(self, *, count: int = 10, block_ms: int = 1_000) -> list[dict[str, Any]]:
        read_map = {stream: ">" for stream in self.subscribed_streams()}
        records = self.bus.read_group(
            self.group_name,
            self.consumer_name,
            read_map,
            count=count,
            block_ms=block_ms,
        )

        handled: list[dict[str, Any]] = []
        for record in records:
            for subscription in self.subscriptions:
                if subscription.stream != record.stream or not subscription.matches(record.event):
                    continue

                outcome = subscription.handler(record) or {}
                self.bus.acknowledge(record.stream, self.group_name, record.event_id)
                handled.append(
                    {
                        "stream": record.stream,
                        "event_id": record.event_id,
                        "event_type": record.event.event_type,
                        "acknowledged": True,
                        "handler_result": outcome,
                    }
                )
                break
            else:
                handled.append(
                    {
                        "stream": record.stream,
                        "event_id": record.event_id,
                        "event_type": record.event.event_type,
                        "acknowledged": False,
                        "handler_result": None,
                    }
                )

        return handled

    def subscribed_streams(self) -> tuple[StreamName, ...]:
        ordered = [subscription.stream for subscription in self.subscriptions]
        return tuple(stream for stream in ALL_STREAMS if stream in ordered)

    @classmethod
    def build_default(cls, *, bus: RedisStreamBus, consumer_role: str) -> "AgentEventConsumer":
        if consumer_role == "scheduler":
            subscriptions = (
                ConsumerRegistration("agent_tasks", DefaultEventHandlers.capture),
                ConsumerRegistration("agent_results", DefaultEventHandlers.capture),
                ConsumerRegistration("ci_events", DefaultEventHandlers.capture),
                ConsumerRegistration("system_events", DefaultEventHandlers.capture),
            )
        else:
            streams = AGENT_STREAM_SUBSCRIPTIONS.get(consumer_role, ("system_events",))
            subscriptions = tuple(
                ConsumerRegistration(stream, DefaultEventHandlers.capture) for stream in streams
            )

        return cls(
            bus=bus,
            group_name=f"{consumer_role}-group",
            consumer_name=f"{consumer_role}-consumer",
            subscriptions=subscriptions,
        )
