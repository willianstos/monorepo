from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from workspace.gateway.providers.base import GenerationOptions, ProviderResult


@dataclass(frozen=True)
class OpenAIAPIProvider:
    name: str = "openai"
    endpoint: str = "https://api.openai.com/v1/chat/completions"

    def generate(self, prompt: str, options: GenerationOptions) -> ProviderResult:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured for OpenAI fallback.")

        payload = json.dumps(
            {
                "model": options.model,
                "messages": options.raw_messages or [{"role": "user", "content": prompt}],
                "temperature": options.temperature,
                "max_tokens": options.max_tokens,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError("OpenAI API fallback is unavailable.") from exc

        content = body["choices"][0]["message"]["content"]
        return ProviderResult(content=content, provider=self.name, model=options.model, raw_output=content)

