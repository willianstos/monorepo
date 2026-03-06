from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "ChatMessage":
        role = str(payload.get("role", "user"))
        content = str(payload.get("content", ""))
        return cls(role=role, content=content)

    def model_dump(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class ChatCompletionRequest:
    model: str = "auto"
    messages: list[ChatMessage] = field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "ChatCompletionRequest":
        messages = [ChatMessage.model_validate(message) for message in payload.get("messages", [])]
        return cls(
            model=str(payload.get("model", "auto")),
            messages=messages,
            temperature=payload.get("temperature"),
            max_tokens=payload.get("max_tokens"),
            metadata=dict(payload.get("metadata", {})),
        )

    def task_text(self) -> str:
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content
        return self.messages[-1].content if self.messages else ""


@dataclass(frozen=True)
class ChatCompletionChoice:
    message: ChatMessage
    finish_reason: str = "stop"
    index: int = 0

    def model_dump(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "finish_reason": self.finish_reason,
            "message": self.message.model_dump(),
        }


@dataclass(frozen=True)
class ChatCompletionResponse:
    model: str
    choices: list[ChatCompletionChoice]
    id: str = field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = field(default_factory=lambda: int(time.time()))

    def model_dump(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [choice.model_dump() for choice in self.choices],
        }
