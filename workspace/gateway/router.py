from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from workspace.gateway.providers import (
    ClaudeCLIProvider,
    CodexCLIProvider,
    GenerationOptions,
    GatewayProvider,
    GeminiCLIProvider,
    OllamaProvider,
    OpenAIAPIProvider,
)
from workspace.gateway.schemas import ChatCompletionChoice, ChatCompletionRequest, ChatCompletionResponse, ChatMessage
from workspace.providers.model_router import ModelRouteDecision, ModelRouter


@dataclass
class GatewayRouter:
    model_router: ModelRouter = field(default_factory=ModelRouter)
    usage_log_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "usage.log"
    )
    _providers: dict[str, GatewayProvider] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._providers = cast(
            dict[str, GatewayProvider],
            {
                "local": OllamaProvider(),
                "codex": CodexCLIProvider(),
                "claude": ClaudeCLIProvider(),
                "gemini": GeminiCLIProvider(),
                "openai": OpenAIAPIProvider(),
            },
        )

    def handle_chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        route = self.route_request(request)
        prompt = self.compose_prompt(request)
        options = GenerationOptions(
            model=route.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            metadata={"task_type": route.task_type, **request.metadata},
            raw_messages=[message.model_dump() for message in request.messages],
        )

        started_at = time.perf_counter()
        provider = self._providers.get(route.provider)
        if provider is None:
            raise ValueError(f"Unsupported provider '{route.provider}'.")
        result = provider.generate(prompt, options)
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        self.log_usage(route, latency_ms)

        return ChatCompletionResponse(
            model=result.model,
            choices=[
                ChatCompletionChoice(
                    message=ChatMessage(role="assistant", content=result.content),
                    finish_reason=result.finish_reason,
                )
            ],
        )

    def route_request(self, request: ChatCompletionRequest) -> ModelRouteDecision:
        model_override = request.model
        task_text = request.metadata.get("task_description") or request.task_text()
        return self.model_router.route_task(task_text, model_override=model_override)

    def compose_prompt(self, request: ChatCompletionRequest) -> str:
        lines: list[str] = []
        for message in request.messages:
            lines.append(f"{message.role.upper()}: {message.content}")
        return "\n\n".join(lines)

    def log_usage(self, route: ModelRouteDecision, latency_ms: int) -> None:
        record = {
            "timestamp": int(time.time()),
            "provider": route.provider,
            "model": route.model,
            "task_type": route.task_type,
            "confidence": route.confidence,
            "backend_type": route.backend_type,
            "transport": route.transport,
            "latency_ms": latency_ms,
        }
        self.usage_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.usage_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
