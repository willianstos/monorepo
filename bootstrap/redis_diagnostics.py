#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any

from workspace.event_bus import RedisStreamBus

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.redis.yml"


def tcp_reachable(host: str, port: int, *, timeout_seconds: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def docker_container_status(container_name: str) -> str | None:
    if shutil.which("docker") is None:
        return None

    completed = subprocess.run(
        ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    status = (completed.stdout or "").strip()
    return status or None


def main() -> None:
    bus = RedisStreamBus()
    socket_ok = tcp_reachable(bus.host, bus.port)
    ping_ok = False
    ping_error: str | None = None
    try:
        ping_ok = bus.ping()
    except Exception as exc:  # noqa: BLE001
        ping_error = str(exc)

    bridge_container = docker_container_status("redis-integration")
    hostnet_container = docker_container_status("redis-hostnet")
    recommended_path = "bridge-compose"
    if bridge_container and not socket_ok:
        recommended_path = "hostnet-compose"
    elif not bridge_container and hostnet_container:
        recommended_path = "hostnet-compose"

    report: dict[str, Any] = {
        "redis_connection": {
            "host": bus.host,
            "port": bus.port,
            "db": bus.db,
            "socket_reachable": socket_ok,
            "redis_ping": ping_ok,
            "ping_error": ping_error,
        },
        "docker": {
            "available": shutil.which("docker") is not None,
            "compose_file": str(COMPOSE_FILE),
            "bridge_container_status": bridge_container,
            "hostnet_container_status": hostnet_container,
        },
        "local_redis_binary_available": shutil.which("redis-server") is not None,
        "recommended_path": recommended_path,
        "commands": {
            "bridge_compose": "docker compose -f docker-compose.redis.yml up -d redis-integration",
            "hostnet_compose": "docker compose -f docker-compose.redis.yml up -d redis-hostnet",
            "health_snapshot": (
                "REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python "
                "bootstrap/local_validation.py snapshot"
            ),
            "scheduler_tests": ".context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py -q",
            "redis_integration_tests": (
                "REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 "
                ".context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q"
            ),
        },
        "notes": [
            "Use redis-integration for the default port-mapped path.",
            "If the container is running but localhost:6380 is unreachable, switch to redis-hostnet.",
            "Keep local validation on a dedicated Redis DB such as REDIS_DB=15 for repeatable runs.",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
