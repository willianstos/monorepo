"""Bounded MCP edge adapters for the local-first assistant workspace."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .adapters import MCPToolDefinition, MemoryMCPAdapter, SchedulerMCPAdapter

if TYPE_CHECKING:
    from .docker_server import DockerMCPServer
    from .server import FutureAgentsMCPServer

__all__ = [
    "DockerMCPServer",
    "FutureAgentsMCPServer",
    "MCPToolDefinition",
    "MemoryMCPAdapter",
    "SchedulerMCPAdapter",
]


def __getattr__(name: str) -> Any:
    if name == "DockerMCPServer":
        from .docker_server import DockerMCPServer

        return DockerMCPServer
    if name == "FutureAgentsMCPServer":
        from .server import FutureAgentsMCPServer

        return FutureAgentsMCPServer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
