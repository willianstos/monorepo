"""Shared tool contracts for agent execution."""

from ._policy import ToolExecutionError, ToolPolicyError
from .filesystem_tool import FilesystemTool
from .git_tool import GitTool
from .terminal_tool import TerminalTool

TOOL_REGISTRY = {
    "filesystem_tool": FilesystemTool,
    "git_tool": GitTool,
    "terminal_tool": TerminalTool,
}

__all__ = [
    "FilesystemTool",
    "GitTool",
    "TOOL_REGISTRY",
    "TerminalTool",
    "ToolExecutionError",
    "ToolPolicyError",
]
