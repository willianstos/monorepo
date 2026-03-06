#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workspace.event_bus import (
    AGENT_RESULT_STREAM,
    AGENT_TASK_STREAM,
    CI_EVENT_STREAM,
    MEMORY_EVENT_STREAM,
    SYSTEM_EVENT_STREAM,
    AgentEvent,
    RedisStreamBus,
)
from workspace.runtime.assistant_runtime import AssistantRuntime

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = REPO_ROOT / "workspace"
LOCAL_VALIDATION_RUNS_ROOT = REPO_ROOT / ".context" / "runs" / "local-validation"


def runtime() -> AssistantRuntime:
    return AssistantRuntime(workspace_root=WORKSPACE_ROOT)


def bus() -> RedisStreamBus:
    return RedisStreamBus()


def publish_event(stream: str, event: AgentEvent) -> dict[str, Any]:
    redis_id = bus().publish(stream, event)
    return {
        "stream": stream,
        "redis_id": redis_id,
        "event": event.to_event_dict(),
    }


def publish(stream: str, event: AgentEvent) -> None:
    print(json.dumps(publish_event(stream, event), indent=2, sort_keys=True))


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def reset_db(*, require_confirmation: bool) -> dict[str, Any]:
    if not require_confirmation:
        raise SystemExit("Refusing to flush Redis without --yes.")

    client = bus().require_client()
    client.flushdb()
    return {
        "status": "redis_db_flushed",
        "connection": bus().connection_info(),
    }


def run_scheduler_cycle(*, count: int, block_ms: int) -> dict[str, Any]:
    return runtime().run_scheduler_cycle(count=count, block_ms=block_ms)


def load_graph_snapshot(graph_id: str) -> dict[str, Any]:
    scheduler = runtime().scheduler_service()
    graph = scheduler.store.load_graph(graph_id)
    client = scheduler.bus.require_client()
    dead_letters = [
        json.loads(item)
        for item in client.lrange(scheduler.store.dead_letter_key(graph_id), 0, -1)
    ]
    tasks = [
        {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "assigned_agent": task.assigned_agent,
            "status": task.status,
            "dependencies": list(task.dependencies),
            "retry_count": task.retry_count,
            "updated_at": task.updated_at,
        }
        for task in sorted(graph.tasks.values(), key=lambda item: item.task_id)
    ]
    return {
        "graph_id": graph.graph_id,
        "status": graph.status,
        "ci_status": graph.ci_status,
        "retry_count": graph.retry_count,
        "max_retry_limit": graph.max_retry_limit,
        "metadata": graph.metadata,
        "tasks": tasks,
        "dead_letters": dead_letters,
    }


def read_stream_records(stream: str, *, count: int) -> list[dict[str, Any]]:
    client = bus().require_client()
    if hasattr(client, "xrevrange"):
        raw_records = list(reversed(client.xrevrange(stream, max="+", min="-", count=count)))
        return [
            {
                "stream": stream,
                "redis_id": str(redis_id),
                "event": AgentEvent.from_dict(fields).to_event_dict(),
            }
            for redis_id, fields in raw_records
        ]

    if hasattr(client, "xrange"):
        raw_records = client.xrange(stream, min="-", max="+", count=count)
        return [
            {
                "stream": stream,
                "redis_id": str(redis_id),
                "event": AgentEvent.from_dict(fields).to_event_dict(),
            }
            for redis_id, fields in raw_records
        ]

    records = bus().read_streams({stream: "0"}, count=count, block_ms=0)
    return [
        {
            "stream": record.stream,
            "redis_id": record.event_id,
            "event": record.event.to_event_dict(),
        }
        for record in records
    ]


def filter_system_events(
    *,
    event_type: str,
    count: int,
    graph_id: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    events = [
        item
        for item in read_stream_records(SYSTEM_EVENT_STREAM, count=count)
        if item["event"]["event_type"] == event_type
    ]
    if graph_id is not None:
        events = [item for item in events if item["event"]["payload"].get("graph_id") == graph_id]
    if category is not None:
        events = [item for item in events if item["event"]["payload"].get("category") == category]
    return events


def write_run_artifact(graph_id: str, payload: dict[str, Any]) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = LOCAL_VALIDATION_RUNS_ROOT / f"{timestamp}-{graph_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / "summary.json"
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


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
    print_json(run_scheduler_cycle(count=args.count, block_ms=args.block_ms))


def memory_once_command(args: argparse.Namespace) -> None:
    print_json(runtime().run_memory_cycle(count=args.count, block_ms=args.block_ms))


def snapshot_command(_: argparse.Namespace) -> None:
    print_json(runtime().scheduler_health_report())


def metrics_command(_: argparse.Namespace) -> None:
    print_json(runtime().scheduler_health_report())


def audit_events_command(args: argparse.Namespace) -> None:
    print_json(
        {
            "stream": SYSTEM_EVENT_STREAM,
            "event_type": args.event_type,
            "graph_id": args.graph_id,
            "category": args.category,
            "events": filter_system_events(
                event_type=args.event_type,
                count=args.count,
                graph_id=args.graph_id,
                category=args.category,
            ),
        }
    )


def graph_state_command(args: argparse.Namespace) -> None:
    print_json(load_graph_snapshot(args.graph_id))


def reset_db_command(args: argparse.Namespace) -> None:
    print_json(reset_db(require_confirmation=args.yes))


def controlled_flow_command(args: argparse.Namespace) -> None:
    if args.reset_db:
        reset_db(require_confirmation=True)

    steps: list[dict[str, Any]] = []
    cycle_kwargs = {"count": args.count, "block_ms": 0}

    def record_step(name: str, *, published: dict[str, Any], cycle: dict[str, Any]) -> None:
        steps.append(
            {
                "step": name,
                "published": published,
                "cycle": cycle,
            }
        )

    record_step(
        "issue_created",
        published=publish_event(
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
        ),
        cycle=run_scheduler_cycle(**cycle_kwargs),
    )
    record_step(
        "plan_task_completed",
        published=publish_event(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="planner",
                correlation_id=args.correlation_id,
                payload={
                    "graph_id": args.graph_id,
                    "task_id": f"{args.graph_id}:plan_task",
                    "project_name": args.project_name,
                },
            ),
        ),
        cycle=run_scheduler_cycle(**cycle_kwargs),
    )
    record_step(
        "implement_task_completed",
        published=publish_event(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="coder",
                correlation_id=args.correlation_id,
                payload={
                    "graph_id": args.graph_id,
                    "task_id": f"{args.graph_id}:implement_task",
                    "project_name": args.project_name,
                    "changed_files": [f"projects/{args.project_name}/src/app.py"],
                },
            ),
        ),
        cycle=run_scheduler_cycle(**cycle_kwargs),
    )
    record_step(
        "test_task_completed",
        published=publish_event(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="tester",
                correlation_id=args.correlation_id,
                payload={
                    "graph_id": args.graph_id,
                    "task_id": f"{args.graph_id}:test_task",
                    "project_name": args.project_name,
                    "changed_files": [f"projects/{args.project_name}/tests/test_app.py"],
                },
            ),
        ),
        cycle=run_scheduler_cycle(**cycle_kwargs),
    )
    record_step(
        "ci_passed",
        published=publish_event(
            CI_EVENT_STREAM,
            AgentEvent.create(
                event_type="ci_passed",
                source="ci",
                correlation_id=args.correlation_id,
                payload={
                    "graph_id": args.graph_id,
                    "project_name": args.project_name,
                },
            ),
        ),
        cycle=run_scheduler_cycle(**cycle_kwargs),
    )
    record_step(
        "review_task_completed",
        published=publish_event(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="reviewer",
                correlation_id=args.correlation_id,
                payload={
                    "graph_id": args.graph_id,
                    "task_id": f"{args.graph_id}:review_task",
                    "project_name": args.project_name,
                },
            ),
        ),
        cycle=run_scheduler_cycle(**cycle_kwargs),
    )
    record_step(
        "merge_attempt_before_approval",
        published=publish_event(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="system",
                correlation_id=args.correlation_id,
                payload={
                    "graph_id": args.graph_id,
                    "task_id": f"{args.graph_id}:merge_task",
                    "project_name": args.project_name,
                },
            ),
        ),
        cycle=run_scheduler_cycle(**cycle_kwargs),
    )
    record_step(
        "human_approval_recorded",
        published=publish_event(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="system",
                correlation_id=args.correlation_id,
                payload={
                    "graph_id": args.graph_id,
                    "task_id": f"{args.graph_id}:human_approval_gate",
                    "project_name": args.project_name,
                    "approval_source": "human",
                    "approval_status": "approved",
                    "approval_actor": args.approval_actor,
                },
            ),
        ),
        cycle=run_scheduler_cycle(**cycle_kwargs),
    )
    record_step(
        "merge_task_completed",
        published=publish_event(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="system",
                correlation_id=args.correlation_id,
                payload={
                    "graph_id": args.graph_id,
                    "task_id": f"{args.graph_id}:merge_task",
                    "project_name": args.project_name,
                },
            ),
        ),
        cycle=run_scheduler_cycle(**cycle_kwargs),
    )

    summary = {
        "status": "completed",
        "graph_id": args.graph_id,
        "project_name": args.project_name,
        "steps": steps,
        "graph": load_graph_snapshot(args.graph_id),
        "health": runtime().scheduler_health_report(),
        "audit_events": filter_system_events(
            event_type="audit_log",
            count=args.audit_count,
            graph_id=args.graph_id,
        ),
        "system_alerts": filter_system_events(
            event_type="system_alert",
            count=args.audit_count,
            graph_id=args.graph_id,
        ),
    }
    artifact_path = write_run_artifact(args.graph_id, summary)
    summary["artifact_path"] = str(artifact_path)
    print_json(summary)


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

    metrics_parser = subparsers.add_parser("metrics", help="Print operator-friendly scheduler metrics.")
    metrics_parser.set_defaults(func=metrics_command)

    audit_parser = subparsers.add_parser("audit-events", help="Inspect audit_log or system_alert events.")
    audit_parser.add_argument("--event-type", default="audit_log", choices=("audit_log", "system_alert"))
    audit_parser.add_argument("--count", type=int, default=50)
    audit_parser.add_argument("--graph-id")
    audit_parser.add_argument("--category")
    audit_parser.set_defaults(func=audit_events_command)

    graph_parser = subparsers.add_parser("graph-state", help="Inspect graph, tasks, and dead-letter state.")
    graph_parser.add_argument("--graph-id", required=True)
    graph_parser.set_defaults(func=graph_state_command)

    reset_parser = subparsers.add_parser("reset-db", help="Flush the current Redis DB used for validation.")
    reset_parser.add_argument("--yes", action="store_true")
    reset_parser.set_defaults(func=reset_db_command)

    flow_parser = subparsers.add_parser(
        "controlled-flow",
        help="Run the local controlled planner->coder->tester->reviewer->approval->merge flow.",
    )
    flow_parser.add_argument("--graph-id", required=True)
    flow_parser.add_argument("--objective", required=True)
    flow_parser.add_argument("--project-name", default="demo-project")
    flow_parser.add_argument("--approval-actor", default="local-operator")
    flow_parser.add_argument("--correlation-id", default="11111111-1111-1111-1111-111111111111")
    flow_parser.add_argument("--count", type=int, default=20)
    flow_parser.add_argument("--audit-count", type=int, default=100)
    flow_parser.add_argument("--reset-db", action="store_true")
    flow_parser.set_defaults(func=controlled_flow_command)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
