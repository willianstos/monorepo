from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any, BinaryIO


from .adapters import MemoryMCPAdapter, SchedulerMCPAdapter, tool_result

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "future-agents-mcp"
SERVER_VERSION = "0.1.0"


class MCPRequestError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class FutureAgentsMCPServer:
    scheduler_adapter: SchedulerMCPAdapter = field(default_factory=SchedulerMCPAdapter.build_default)
    memory_adapter: MemoryMCPAdapter = field(default_factory=MemoryMCPAdapter.build_default)
    protocol_version: str = PROTOCOL_VERSION
    initialized: bool = False

    def tool_definitions(self) -> list[dict[str, Any]]:
        tools = self.scheduler_adapter.tool_definitions() + self.memory_adapter.tool_definitions()
        return [tool.to_dict() for tool in tools]

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = str(message.get("method") or "").strip()
        request_id = message.get("id")

        if not method:
            raise MCPRequestError(-32600, "Invalid request: method is required.")

        if method == "notifications/initialized":
            self.initialized = True
            return None

        if method == "initialize":
            self.initialized = True
            return self._result(
                request_id,
                {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            )

        if not self.initialized:
            raise MCPRequestError(-32002, "Server not initialized.")

        if method == "ping":
            return self._result(request_id, {})
        if method == "tools/list":
            return self._result(request_id, {"tools": self.tool_definitions()})
        if method == "tools/call":
            params = message.get("params", {})
            if not isinstance(params, dict):
                raise MCPRequestError(-32602, "tools/call params must be an object.")
            name = str(params.get("name") or "").strip()
            arguments = params.get("arguments", {})
            if not name:
                raise MCPRequestError(-32602, "tools/call requires a tool name.")
            if not isinstance(arguments, dict):
                raise MCPRequestError(-32602, "tools/call arguments must be an object.")
            return self._result(request_id, self._call_tool(name=name, arguments=arguments))

        raise MCPRequestError(-32601, f"Method '{method}' not found.")

    def serve_stdio(self, input_stream: BinaryIO | None = None, output_stream: BinaryIO | None = None) -> int:
        input_stream = input_stream or sys.stdin.buffer
        output_stream = output_stream or sys.stdout.buffer

        while True:
            try:
                message = self._read_message(input_stream)
            except EOFError:
                break
            except Exception as exc:  # noqa: BLE001
                logging.debug("stdio read failed: %s", exc)
                self._write_response(output_stream, self._error(None, -32700, "Parse error."))
                continue

            if message is None:
                break

            try:
                response = self.handle_message(message)
            except MCPRequestError as exc:
                response = self._error(message.get("id"), exc.code, exc.message)
            except Exception as exc:  # noqa: BLE001
                response = self._error(message.get("id"), -32603, f"Internal error: {exc}")

            if response is not None:
                self._write_response(output_stream, response)

        return 0

    @staticmethod
    def _read_headers(input_stream: BinaryIO) -> dict[str, str]:
        headers: dict[str, str] = {}

        while True:
            line = input_stream.readline()
            if line == b"":
                raise EOFError

            if line in (b"\r\n", b"\n"):
                return headers

            if not line.endswith((b"\n",)):
                raise ValueError("Invalid MCP frame: incomplete header line.")

            text = line.decode("utf-8").strip()
            if not text:
                return headers

            name, sep, value = text.partition(":")
            if not sep:
                raise ValueError("Invalid MCP frame header: missing separator.")

            headers[name.strip().lower()] = value.strip()

    @staticmethod
    def _read_message(input_stream: BinaryIO) -> dict[str, Any] | None:
        headers = FutureAgentsMCPServer._read_headers(input_stream)
        if "content-length" not in headers:
            raise ValueError("Invalid MCP frame: missing Content-Length header.")

        try:
            content_length = int(headers["content-length"])
        except ValueError as exc:
            raise ValueError("Invalid MCP frame: invalid Content-Length.") from exc

        if content_length < 0:
            raise ValueError("Invalid MCP frame: negative Content-Length.")

        payload = input_stream.read(content_length)
        if len(payload) < content_length:
            raise ValueError("Invalid MCP frame: incomplete body.")

        try:
            return json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid MCP frame: invalid JSON.") from exc

    @staticmethod
    def _write_response(output_stream: BinaryIO, response: dict[str, Any]) -> None:
        payload = json.dumps(response, sort_keys=True).encode("utf-8")
        header = f"Content-Length: {len(payload)}\r\n\r\n"
        output_stream.write(header.encode("utf-8"))
        output_stream.write(payload)
        output_stream.flush()

    def _call_tool(self, *, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.scheduler_adapter.supports_tool(name):
                payload = self.scheduler_adapter.call_tool(name, arguments)
                return tool_result(payload)
            if self.memory_adapter.supports_tool(name):
                payload = self.memory_adapter.call_tool(name, arguments)
                is_error = str(payload.get("status")) == "rejected"
                return tool_result(payload, is_error=is_error)
            raise MCPRequestError(-32602, f"Unsupported tool '{name}'.")
        except MCPRequestError:
            raise
        except (KeyError, ValueError) as exc:
            raise MCPRequestError(-32602, str(exc)) from exc

    @staticmethod
    def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Future Agents local-first MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio",),
        default="stdio",
        help="Epic 1 exposes stdio only. HTTP/SSE remains out of scope.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    server = FutureAgentsMCPServer()
    if args.transport != "stdio":
        raise SystemExit("Only stdio transport is supported in Epic 1.")
    return server.serve_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
