from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from workspace.event_bus import MEMORY_EVENT_STREAM, SYSTEM_EVENT_STREAM, AgentEvent, RedisStreamBus, build_audit_payload
from workspace.memory.manager import MemoryManager
from workspace.memory.schemas import MemoryRecord, MemoryType
from workspace.scheduler.guardrail_enforcer import GuardrailEnforcer

MEMORY_INPUT_EVENTS: tuple[str, ...] = ("memory_write_requested",)


@dataclass
class MemoryRuntimeService:
    bus: RedisStreamBus
    guardrails: GuardrailEnforcer
    manager: MemoryManager = field(default_factory=MemoryManager)
    group_name: str = "memory-group"
    consumer_name: str = "memory-runtime"

    @classmethod
    def build_default(cls, *, rules_root: Path | None = None) -> "MemoryRuntimeService":
        return cls(
            bus=RedisStreamBus(),
            guardrails=GuardrailEnforcer(rules_root=rules_root),
        )

    def describe(self) -> dict[str, Any]:
        return {
            "service": "memory_runtime",
            "group_name": self.group_name,
            "consumer_name": self.consumer_name,
            "input_events": list(MEMORY_INPUT_EVENTS),
            "runtime_keys": self.manager.runtime_keys(
                project_name="{project_name}",
                graph_id="{graph_id}",
                task_id="{task_id}",
            ),
        }

    def ensure_group(self) -> None:
        self.bus.ensure_consumer_group(MEMORY_EVENT_STREAM, self.group_name, start_id="0")

    def run_once(self, *, count: int = 20, block_ms: int = 1_000) -> list[dict[str, Any]]:
        self.ensure_group()
        records = self.bus.read_group(
            self.group_name,
            self.consumer_name,
            {MEMORY_EVENT_STREAM: ">"},
            count=count,
            block_ms=block_ms,
        )

        handled: list[dict[str, Any]] = []
        for record in records:
            outcome = self.handle_event(record.event)
            self.bus.acknowledge(MEMORY_EVENT_STREAM, self.group_name, record.event_id)
            handled.append(
                {
                    "stream": record.stream,
                    "event_id": record.event_id,
                    "event_type": record.event.event_type,
                    "handler_result": outcome,
                }
            )
        return handled

    def handle_event(self, event: AgentEvent) -> dict[str, Any]:
        if event.event_type not in MEMORY_INPUT_EVENTS:
            return {"status": "ignored", "event_type": event.event_type}

        decision = self.guardrails.validate_memory_payload(event.payload)
        graph_id = str(event.payload.get("graph_id") or "")
        task_id = str(event.payload.get("task_id") or "")
        task_type = str(event.payload.get("task_type") or "memory_write_requested")
        if not decision.allowed:
            reason = self._format_violations(decision.to_dict()["violations"])
            self._publish_system_alert(event, reason)
            self._publish_audit_log(
                event,
                graph_id=graph_id,
                task_id=task_id,
                task_type=task_type,
                reason=reason,
                result="rejected",
            )
            return {
                "status": "memory_payload_rejected",
                "graph_id": graph_id,
                "task_id": task_id,
                "violations": decision.to_dict()["violations"],
            }

        records = [self._coerce_record(record) for record in event.payload.get("records", [])]
        persisted = self.manager.persist_runtime_records(
            self.bus.require_client(),
            project_name=str(event.payload.get("project_name") or "unknown"),
            graph_id=graph_id,
            task_id=task_id,
            records=records,
        )
        self._publish_audit_log(
            event,
            graph_id=graph_id,
            task_id=task_id,
            task_type=task_type,
            reason=f"Persisted {persisted['records_persisted']} distilled memory records.",
            result="accepted",
        )
        return {
            "status": "memory_persisted",
            "graph_id": graph_id,
            "task_id": task_id,
            "records_persisted": persisted["records_persisted"],
            "keys": persisted["keys"],
        }

    @staticmethod
    def _coerce_record(record: dict[str, Any]) -> MemoryRecord:
        return {
            "memory_type": cast(MemoryType, record["memory_type"]),
            "topic": str(record["topic"]).strip(),
            "summary": str(record["summary"]).strip(),
            "confidence": float(record["confidence"]),
            "tags": [str(tag).strip() for tag in record["tags"]],
        }

    def _publish_system_alert(self, event: AgentEvent, reason: str) -> None:
        self.bus.publish(
            SYSTEM_EVENT_STREAM,
            AgentEvent.create(
                event_type="system_alert",
                source="system",
                correlation_id=event.correlation_id,
                payload={
                    "graph_id": event.payload.get("graph_id"),
                    "task_id": event.payload.get("task_id"),
                    "severity": "warning",
                    "message": reason,
                },
            ),
        )

    def _publish_audit_log(
        self,
        event: AgentEvent,
        *,
        graph_id: str,
        task_id: str,
        task_type: str,
        reason: str,
        result: str,
    ) -> None:
        payload = build_audit_payload(
            event,
            graph_id=graph_id,
            task_id=task_id,
            task_type=task_type,
            reason=reason,
            category="memory",
            result=result,
        )
        self.bus.publish(
            SYSTEM_EVENT_STREAM,
            AgentEvent.create(
                event_type="audit_log",
                source="system",
                correlation_id=event.correlation_id,
                payload=payload,
            ),
        )

    @staticmethod
    def _format_violations(violations: list[dict[str, Any]]) -> str:
        return "; ".join(str(violation.get("message", "")) for violation in violations if violation.get("message"))
