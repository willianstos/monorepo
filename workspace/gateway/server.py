from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from workspace.gateway.router import GatewayRouter
from workspace.gateway.schemas import ChatCompletionRequest


class GatewayRequestHandler(BaseHTTPRequestHandler):
    router = GatewayRouter()

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "local-llm-gateway"})
            return

        if self.path == "/v1/models":
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [
                        {"id": "auto", "object": "model"},
                        {"id": "local:qwen3.5-9b", "object": "model"},
                        {"id": "codex-cli", "object": "model"},
                        {"id": "claude-code", "object": "model"},
                        {"id": "gemini", "object": "model"},
                        {"id": "openai", "object": "model"},
                    ],
                },
            )
            return

        self._send_json(404, {"error": {"message": "Not found"}})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "Not found"}})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(content_length).decode("utf-8")
            request_body = ChatCompletionRequest.model_validate(json.loads(payload))
            response = self.router.handle_chat_completion(request_body)
            self._send_json(200, response.model_dump())
        except (json.JSONDecodeError, TypeError, ValueError):
            self._send_json(400, {"error": {"message": "Invalid chat completion request payload."}})
        except Exception:  # noqa: BLE001
            self._send_json(502, {"error": {"message": "Gateway backend execution failed."}})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = "127.0.0.1", port: int = 4000) -> None:
    server = ThreadingHTTPServer((host, port), GatewayRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
