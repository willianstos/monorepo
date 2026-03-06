from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from workspace.gateway.providers.base import GenerationOptions, ProviderResult


@dataclass(frozen=True)
class OllamaProvider:
    name: str = "local"
    endpoint: str = "http://localhost:11434/api/generate"

    def generate(self, prompt: str, options: GenerationOptions) -> ProviderResult:
        payload = json.dumps(
            {
                "model": options.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": options.temperature,
                    "num_predict": options.max_tokens,
                },
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError("Ollama endpoint is unavailable.") from exc

        content = body.get("response", "")
        return ProviderResult(content=content, provider=self.name, model=options.model, raw_output=content)

