#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from workspace.event_bus import (
    AGENT_RESULT_STREAM,
    AGENT_TASK_STREAM,
    CI_EVENT_STREAM,
    MEMORY_EVENT_STREAM,
    AgentEvent,
    RedisStreamBus,
)
from workspace.runtime.assistant_runtime import AssistantRuntime

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = REPO_ROOT / "workspace"


def runtime() -> AssistantRuntime:
    return AssistantRuntime(workspace_root=WORKSPACE_ROOT)


def bus() -> RedisStreamBus:
    return RedisStreamBus()


def publish(stream: str, event: AgentEvent) -> None:
    redis_id = bus().publish(stream, event)
    print(
        json.dumps(
            {
                "stream": stream,
                "redis_id": redis_id,
                "event": event.to_event_dict(),
            },
            indent=2,
            sort_keys=True,
        )
    )


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def issue_command(args: argparse.Namespace) -> None:
    publish(
        AGENT_TASK_STREAM,
        AgentEvent.create(
            event_type="issue_created",
            source="planner",
            correlation_id=args.correlation_id,
            payload={
                "graph_id": args.graph_id,
                "task_id": args.graph_id,
                "project_name": args.project_name,
                "objective": args.objective,
            },
        ),
    )


def task_result_command(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {
        "graph_id": args.graph_id,
        "task_id": args.task_id,
        "project_name": args.project_name,
    }
    if args.task_type:
        payload["task_type"] = args.task_type
    if args.reason:
        payload["reason"] = args.reason
    if args.changed_files:
        payload["changed_files"] = list(args.changed_files)

    publish(
        AGENT_RESULT_STREAM,
        AgentEvent.create(
            event_type=args.event_type,
            source=args.source,
            correlation_id=args.correlation_id,
            payload=payload,
        ),
    )


def ci_event_command(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {
        "graph_id": args.graph_id,
        "project_name": args.project_name,
    }
    if args.reason:
        payload["reason"] = args.reason

    publish(
        CI_EVENT_STREAM,
        AgentEvent.create(
            event_type=args.event_type,
            source="ci",
            correlation_id=args.correlation_id,
            payload=payload,
        ),
    )


def approve_command(args: argparse.Namespace) -> None:
    publish(
        AGENT_RESULT_STREAM,
        AgentEvent.create(
            event_type="task_completed",
            source="system",
            correlation_id=args.correlation_id,
            payload={
                "graph_id": args.graph_id,
                "task_id": args.task_id or f"{args.graph_id}:human_approval_gate",
                "project_name": args.project_name,
                "approval_source": args.approval_source,
                "approval_status": args.approval_status,
                "approval_actor": args.approval_actor,
            },
        ),
    )


def merge_complete_command(args: argparse.Namespace) -> None:
    publish(
        AGENT_RESULT_STREAM,
        AgentEvent.create(
            event_type="task_completed",
            source="system",
            correlation_id=args.correlation_id,
            payload={
                "graph_id": args.graph_id,
                "task_id": args.task_id or f"{args.graph_id}:merge_task",
                "project_name": args.project_name,
            },
        ),
    )


def memory_write_command(args: argparse.Namespace) -> None:
    records = json.loads(args.records_json)
    publish(
        MEMORY_EVENT_STREAM,
        AgentEvent.create(
            event_type="memory_write_requested",
            source="system",
            correlation_id=args.correlation_id,
            payload={
                "graph_id": args.graph_id,
                "task_id": args.task_id,
                "project_name": args.project_name,
                "records": records,
            },
        ),
    )


def scheduler_once_command(args: argparse.Namespace) -> None:
    print_json(runtime().run_scheduler_cycle(count=args.count, block_ms=args.block_ms))


def memory_once_command(args: argparse.Namespace) -> None:
    print_json(runtime().run_memory_cycle(count=args.count, block_ms=args.block_ms))


def snapshot_command(_: argparse.Namespace) -> None:
    print_json(runtime().scheduler_health_report())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local orchestration validation helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue_parser = subparsers.add_parser("issue", help="Publish an issue_created event.")
    issue_parser.add_argument("--graph-id", required=True)
    issue_parser.add_argument("--objective", required=True)
    issue_parser.add_argument("--project-name", default="demo-project")
    issue_parser.add_argument("--correlation-id", default="11111111-1111-1111-1111-111111111111")
    issue_parser.set_defaults(func=issue_command)

    result_parser = subparsers.add_parser("task-result", help="Publish a planner/coder/tester/reviewer result.")
    result_parser.add_argument("--graph-id", required=True)
    result_parser.add_argument("--task-id", required=True)
    result_parser.add_argument(
        "--source",
        required=True,
        choices=("planner", "coder", "tester", "reviewer", "system"),
    )
    result_parser.add_argument(
        "--event-type",
        required=True,
        choices=("task_started", "task_completed", "task_failed", "code_generated"),
    )
    result_parser.add_argument("--project-name", default="demo-project")
    result_parser.add_argument("--task-type")
    result_parser.add_argument("--reason")
    result_parser.add_argument("--changed-files", nargs="*")
    result_parser.add_argument("--correlation-id", default="11111111-1111-1111-1111-111111111111")
    result_parser.set_defaults(func=task_result_command)

    ci_parser = subparsers.add_parser("ci-event", help="Publish an authoritative CI event.")
    ci_parser.add_argument(
        "--event-type",
        required=True,
        choices=("ci_started", "ci_failed", "ci_passed", "coverage_failed", "security_failed"),
    )
    ci_parser.add_argument("--graph-id", required=True)
    ci_parser.add_argument("--project-name", default="demo-project")
    ci_parser.add_argument("--reason")
    ci_parser.add_argument("--correlation-id", default="11111111-1111-1111-1111-111111111111")
    ci_parser.set_defaults(func=ci_event_command)

    approve_parser = subparsers.add_parser("approve", help="Publish a trusted human approval result.")
    approve_parser.add_argument("--graph-id", required=True)
    approve_parser.add_argument("--task-id")
    approve_parser.add_argument("--project-name", default="demo-project")
    approve_parser.add_argument("--approval-source", default="human", choices=("human", "system"))
    approve_parser.add_argument("--approval-status", default="approved", choices=("approved", "rejected"))
    approve_parser.add_argument("--approval-actor", default="local-operator")
    approve_parser.add_argument("--correlation-id", default="11111111-1111-1111-1111-111111111111")
    approve_parser.set_defaults(func=approve_command)

    merge_parser = subparsers.add_parser("merge-complete", help="Publish a merge completion result.")
    merge_parser.add_argument("--graph-id", required=True)
    merge_parser.add_argument("--task-id")
    merge_parser.add_argument("--project-name", default="demo-project")
    merge_parser.add_argument("--correlation-id", default="11111111-1111-1111-1111-111111111111")
    merge_parser.set_defaults(func=merge_complete_command)

    memory_parser = subparsers.add_parser("memory-write", help="Publish a memory_write_requested event.")
    memory_parser.add_argument("--graph-id", required=True)
    memory_parser.add_argument("--task-id", required=True)
    memory_parser.add_argument("--project-name", default="demo-project")
    memory_parser.add_argument("--records-json", required=True)
    memory_parser.add_argument("--correlation-id", default="11111111-1111-1111-1111-111111111111")
    memory_parser.set_defaults(func=memory_write_command)

    scheduler_parser = subparsers.add_parser("scheduler-once", help="Run one scheduler cycle.")
    scheduler_parser.add_argument("--count", type=int, default=20)
    scheduler_parser.add_argument("--block-ms", type=int, default=0)
    scheduler_parser.set_defaults(func=scheduler_once_command)

    memory_once_parser = subparsers.add_parser("memory-once", help="Run one memory runtime cycle.")
    memory_once_parser.add_argument("--count", type=int, default=20)
    memory_once_parser.add_argument("--block-ms", type=int, default=0)
    memory_once_parser.set_defaults(func=memory_once_command)

    snapshot_parser = subparsers.add_parser("snapshot", help="Print scheduler observability snapshot.")
    snapshot_parser.set_defaults(func=snapshot_command)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

