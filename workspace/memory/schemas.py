from __future__ import annotations

from typing import Literal, TypedDict

MemoryType = Literal["learning", "decision", "architecture", "bug", "improvement"]


class MemoryRecord(TypedDict):
    memory_type: MemoryType
    topic: str
    summary: str
    confidence: float
    tags: list[str]


class RetrievedMemory(TypedDict):
    memory_type: MemoryType
    topic: str
    summary: str
    confidence: float
    tags: list[str]
    source_layer: Literal["structured_memory", "recent_sessions"]
