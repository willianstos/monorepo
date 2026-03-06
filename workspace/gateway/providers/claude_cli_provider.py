from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from workspace.gateway.providers.base import GenerationOptions, ProviderResult
from workspace.gateway.providers.cli_utils import CLISandboxExecutor


@dataclass(frozen=True)
class ClaudeCLIProvider:
    name: str = "claude"
    credential_path: Path = Path.home() / ".anthropic"
    executor: CLISandboxExecutor = field(default_factory=CLISandboxExecutor)

    def generate(self, prompt: str, options: GenerationOptions) -> ProviderResult:
        command = self.executor.parse_command("LLM_GATEWAY_CLAUDE_CMD", "claude")
        output = self.executor.run(command, prompt=prompt)
        return ProviderResult(content=output, provider=self.name, model=options.model, raw_output=output)

