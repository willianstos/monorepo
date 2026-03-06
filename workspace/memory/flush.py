from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from workspace.memory.manager import MemoryManager
from workspace.memory.schemas import MemoryRecord


@dataclass
class MemoryFlushService:
    manager: MemoryManager = field(default_factory=MemoryManager)

    def flush_session(
        self,
        *,
        decisions: Iterable[tuple[str, str, float, list[str]]] = (),
        facts: Iterable[tuple[str, str, float, list[str]]] = (),
        architecture_updates: Iterable[tuple[str, str, float, list[str]]] = (),
        bugs: Iterable[tuple[str, str, float, list[str]]] = (),
        fixes: Iterable[tuple[str, str, float, list[str]]] = (),
        lessons: Iterable[tuple[str, str, float, list[str]]] = (),
        performance_insights: Iterable[tuple[str, str, float, list[str]]] = (),
    ) -> dict[str, object]:
        records: list[MemoryRecord] = []

        records.extend(
            self.manager.build_record("decision", topic, summary, confidence, tags)
            for topic, summary, confidence, tags in decisions
        )
        records.extend(
            self.manager.build_record("learning", topic, summary, confidence, tags)
            for topic, summary, confidence, tags in facts
        )
        records.extend(
            self.manager.build_record("architecture", topic, summary, confidence, tags)
            for topic, summary, confidence, tags in architecture_updates
        )
        records.extend(
            self.manager.build_record("bug", topic, summary, confidence, tags)
            for topic, summary, confidence, tags in bugs
        )
        records.extend(
            self.manager.build_record("improvement", topic, summary, confidence, tags)
            for topic, summary, confidence, tags in fixes
        )
        records.extend(
            self.manager.build_record("learning", topic, summary, confidence, tags)
            for topic, summary, confidence, tags in lessons
        )
        records.extend(
            self.manager.build_record("improvement", topic, summary, confidence, tags)
            for topic, summary, confidence, tags in performance_insights
        )

        return self.manager.flush(records)

