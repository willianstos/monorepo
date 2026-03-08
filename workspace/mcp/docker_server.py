from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, BinaryIO

from .adapters import MCPToolDefinition, tool_result

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "future-agents-docker-mcp"
SERVER_VERSION = "0.1.0"


class MCPRequestError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DockerCommandResult:
    args: list[str]
    exit_code: int
    stdout: str
    stderr: str


@dataclass
class DockerMCPServer:
    protocol_version: str = PROTOCOL_VERSION
    initialized: bool = False

    def tool_definitions(self) -> list[dict[str, Any]]:
        tools = [
            MCPToolDefinition(
                name="docker_list_containers",
                title="List Containers",
                description="List Docker containers visible to the local Docker daemon.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "all": {"type": "boolean", "default": False},
                    },
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="docker_inspect_container",
                title="Inspect Container",
                description="Return the full docker inspect payload for one container.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "container_id": {"type": "string"},
                    },
                    "required": ["container_id"],
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="docker_container_logs",
                title="Container Logs",
                description="Return recent logs for one container.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "container_id": {"type": "string"},
                        "tail": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
                        "timestamps": {"type": "boolean", "default": False},
                    },
                    "required": ["container_id"],
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="docker_exec",
                title="Exec In Container",
                description="Run a command inside a running container.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "container_id": {"type": "string"},
                        "command": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}, "minItems": 1},
                            ]
                        },
                    },
                    "required": ["container_id", "command"],
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="docker_list_images",
                title="List Images",
                description="List Docker images available on the local Docker daemon.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            MCPToolDefinition(
                name="docker_version",
                title="Docker Version",
                description="Return docker client and server version details.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
        ]
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

            try:
                response = self.handle_message(message)
            except MCPRequestError as exc:
                response = self._error(message.get("id"), exc.code, exc.message)
            except Exception as exc:  # noqa: BLE001
                response = self._error(message.get("id"), -32603, f"Internal error: {exc}")

            if response is not None:
                self._write_response(output_stream, response)

        return 0

    def _call_tool(self, *, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "docker_list_containers":
            payload = self._list_containers(all_containers=bool(arguments.get("all")))
            return tool_result(payload, is_error=payload["status"] == "error")
        if name == "docker_inspect_container":
            return self._inspect_container(container_id=self._require_non_empty(arguments, "container_id"))
        if name == "docker_container_logs":
            return self._container_logs(
                container_id=self._require_non_empty(arguments, "container_id"),
                tail=self._coerce_tail(arguments.get("tail", 100)),
                timestamps=bool(arguments.get("timestamps")),
            )
        if name == "docker_exec":
            return self._exec_in_container(
                container_id=self._require_non_empty(arguments, "container_id"),
                command=arguments.get("command"),
            )
        if name == "docker_list_images":
            payload = self._list_images()
            return tool_result(payload, is_error=payload["status"] == "error")
        if name == "docker_version":
            return self._docker_version()
        raise MCPRequestError(-32602, f"Unsupported tool '{name}'.")

    def _list_containers(self, *, all_containers: bool) -> dict[str, Any]:
        args = ["ps", "--format", "{{json .}}"]
        if all_containers:
            args.insert(1, "-a")
        result = self._run_docker(args)
        if result.exit_code != 0:
            return self._error_payload(result, "docker_list_containers")
        containers = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        return {
            "status": "ok",
            "all": all_containers,
            "count": len(containers),
            "containers": containers,
        }

    def _inspect_container(self, *, container_id: str) -> dict[str, Any]:
        result = self._run_docker(["inspect", container_id])
        if result.exit_code != 0:
            return tool_result(self._error_payload(result, "docker_inspect_container"), is_error=True)
        return tool_result(
            {
                "status": "ok",
                "container_id": container_id,
                "inspection": json.loads(result.stdout),
            }
        )

    def _container_logs(self, *, container_id: str, tail: int, timestamps: bool) -> dict[str, Any]:
        args = ["logs", "--tail", str(tail)]
        if timestamps:
            args.append("--timestamps")
        args.append(container_id)
        result = self._run_docker(args)
        if result.exit_code != 0:
            return tool_result(self._error_payload(result, "docker_container_logs"), is_error=True)
        return tool_result(
            {
                "status": "ok",
                "container_id": container_id,
                "tail": tail,
                "timestamps": timestamps,
                "logs": result.stdout,
            }
        )

    def _exec_in_container(self, *, container_id: str, command: Any) -> dict[str, Any]:
        exec_args = self._coerce_exec_command(command)
        result = self._run_docker(["exec", container_id, *exec_args], timeout_seconds=60)
        payload = {
            "status": "ok" if result.exit_code == 0 else "error",
            "container_id": container_id,
            "command": exec_args,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        return tool_result(payload, is_error=result.exit_code != 0)

    def _list_images(self) -> dict[str, Any]:
        result = self._run_docker(["images", "--format", "{{json .}}"])
        if result.exit_code != 0:
            return self._error_payload(result, "docker_list_images")
        images = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        return {
            "status": "ok",
            "count": len(images),
            "images": images,
        }

    def _docker_version(self) -> dict[str, Any]:
        result = self._run_docker(["version", "--format", "{{json .}}"])
        if result.exit_code != 0:
            return tool_result(self._error_payload(result, "docker_version"), is_error=True)
        return tool_result(
            {
                "status": "ok",
                "version": json.loads(result.stdout),
            }
        )

    def _run_docker(self, args: list[str], *, timeout_seconds: int = 30) -> DockerCommandResult:
        if shutil.which("docker") is None:
            return DockerCommandResult(args=args, exit_code=127, stdout="", stderr="docker CLI not found.")

        completed = subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return DockerCommandResult(
            args=["docker", *args],
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    @staticmethod
    def _error_payload(result: DockerCommandResult, tool_name: str) -> dict[str, Any]:
        return {
            "status": "error",
            "tool": tool_name,
            "command": result.args,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    @staticmethod
    def _require_non_empty(arguments: dict[str, Any], key: str) -> str:
        value = str(arguments.get(key, "")).strip()
        if not value:
            raise MCPRequestError(-32602, f"'{key}' is required.")
        return value

    @staticmethod
    def _coerce_tail(value: Any) -> int:
        try:
            tail = int(value)
        except (TypeError, ValueError) as exc:
            raise MCPRequestError(-32602, "'tail' must be an integer.") from exc
        if tail < 1 or tail > 1000:
            raise MCPRequestError(-32602, "'tail' must be between 1 and 1000.")
        return tail

    @staticmethod
    def _coerce_exec_command(value: Any) -> list[str]:
        if isinstance(value, str) and value.strip():
            return ["sh", "-lc", value]
        if isinstance(value, list) and value and all(isinstance(item, str) and item for item in value):
            return value
        raise MCPRequestError(-32602, "'command' must be a non-empty string or string array.")

    @staticmethod
    def _read_headers(input_stream: BinaryIO) -> dict[str, str]:
        headers: dict[str, str] = {}

        while True:
            line = input_stream.readline()
            if line == b"":
                raise EOFError
            if line in (b"\r\n", b"\n"):
                return headers
            if not line.endswith(b"\n"):
                raise ValueError("Invalid MCP frame: incomplete header line.")

            text = line.decode("utf-8").strip()
            if not text:
                return headers
            name, sep, value = text.partition(":")
            if not sep:
                raise ValueError("Invalid MCP frame header: missing separator.")
            headers[name.strip().lower()] = value.strip()

    @staticmethod
    def _read_message(input_stream: BinaryIO) -> dict[str, Any]:
        headers = DockerMCPServer._read_headers(input_stream)
        if "content-length" not in headers:
            raise ValueError("Invalid MCP frame: missing Content-Length header.")

        content_length = int(headers["content-length"])
        payload = input_stream.read(content_length)
        if len(payload) < content_length:
            raise ValueError("Invalid MCP frame: incomplete body.")
        return json.loads(payload.decode("utf-8"))

    @staticmethod
    def _write_response(output_stream: BinaryIO, response: dict[str, Any]) -> None:
        payload = json.dumps(response, sort_keys=True).encode("utf-8")
        output_stream.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8"))
        output_stream.write(payload)
        output_stream.flush()

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
    parser = argparse.ArgumentParser(description="Local Docker MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio",),
        default="stdio",
        help="Expose the Docker MCP server over stdio.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    server = DockerMCPServer()
    if args.transport != "stdio":
        raise SystemExit("Only stdio transport is supported.")
    return server.serve_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
