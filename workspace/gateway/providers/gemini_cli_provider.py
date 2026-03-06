from __future__ import annotations

from dataclasses import dataclass, field

from workspace.gateway.providers.base import GenerationOptions, ProviderResult
from workspace.gateway.providers.cli_utils import CLISandboxExecutor


@dataclass(frozen=True)
class GeminiCLIProvider:
    name: str = "gemini"
    credential_hint: str = "Uses existing Google OAuth session managed by Antigravity or Gemini CLI."
    executor: CLISandboxExecutor = field(default_factory=CLISandboxExecutor)

    def generate(self, prompt: str, options: GenerationOptions) -> ProviderResult:
        command = self.executor.parse_command("LLM_GATEWAY_GEMINI_CMD", "gemini")
        output = self.executor.run(command, prompt=prompt)
        return ProviderResult(content=output, provider=self.name, model=options.model, raw_output=output)

