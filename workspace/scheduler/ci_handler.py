from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from workspace.event_bus import AgentEvent
from workspace.scheduler.dag_builder import DagBuilder, TaskGraph, TaskNode, TaskStatus

CI_EVENT_TYPES: tuple[str, ...] = (
    "ci_started",
    "ci_failed",
    "ci_passed",
    "coverage_failed",
    "security_failed",
)


@dataclass(frozen=True)
class CITransitionPlan:
    task_id: str
    task_type: str
    target_status: TaskStatus
    reason: str


@dataclass(frozen=True)
class CIHandlingPlan:
    graph_id: str
    ci_status: str
    dispatch_ready_tasks: bool
    graph_status: str | None = None
    metadata_updates: dict[str, Any] = field(default_factory=dict)
    transition_plans: tuple[CITransitionPlan, ...] = ()
    block_ci_gated_tasks: bool = False
    increment_retry: bool = False
    new_tasks: tuple[TaskNode, ...] = ()
    system_alerts: tuple[dict[str, Any], ...] = ()
    valid: bool = True
    reason: str | None = None


@dataclass
class CIEventHandler:
    """Translate authoritative CI events into scheduler-applied mutations."""

    builder: DagBuilder

    def describe(self) -> dict[str, Any]:
        return {
            "ci_source": "argo",
            "event_types": list(CI_EVENT_TYPES),
            "source_of_truth": True,
            "fix_loop_supported": True,
            "task_state_mutations": "scheduler_only",
        }

    def handle(self, event: AgentEvent, graph: TaskGraph) -> CIHandlingPlan:
        graph_id = self._resolve_graph_id(event)
        metadata_updates = {
            "last_ci_event": event.event_type,
            "last_ci_payload": dict(event.payload),
        }

        if event.event_type == "ci_started":
            rerun_task = self._find_last_fix_loop_task(graph, "last_rerun_ci_task_id", "rerun_ci")
            if rerun_task is None:
                return self._invalid_plan(
                    graph_id=graph_id,
                    ci_status=graph.ci_status,
                    metadata_updates=metadata_updates,
                    reason="ci_started requires an existing rerun_ci task.",
                )
            if rerun_task.status != "ready":
                return self._invalid_plan(
                    graph_id=graph_id,
                    ci_status=graph.ci_status,
                    metadata_updates=metadata_updates,
                    reason=(
                        "ci_started requires rerun_ci to be ready before it can transition to running."
                    ),
                )
            return CIHandlingPlan(
                graph_id=graph_id,
                ci_status="running",
                graph_status="active",
                dispatch_ready_tasks=False,
                metadata_updates=metadata_updates,
                transition_plans=(
                    CITransitionPlan(
                        task_id=rerun_task.task_id,
                        task_type=rerun_task.task_type,
                        target_status="running",
                        reason="CI rerun has started.",
                    ),
                ),
            )

        if event.event_type == "ci_passed":
            rerun_task = self._find_last_fix_loop_task(graph, "last_rerun_ci_task_id", "rerun_ci")
            transition_plans: tuple[CITransitionPlan, ...] = ()
            if rerun_task is not None:
                fix_task = self._find_last_fix_loop_task(graph, "last_fix_task_id", "fix_task")
                if fix_task is None or fix_task.status != "completed":
                    return self._invalid_plan(
                        graph_id=graph_id,
                        ci_status=graph.ci_status,
                        metadata_updates=metadata_updates,
                        reason="ci_passed requires the latest fix_task to be completed first.",
                    )
                if rerun_task.status != "running":
                    return self._invalid_plan(
                        graph_id=graph_id,
                        ci_status=graph.ci_status,
                        metadata_updates=metadata_updates,
                        reason="ci_passed requires rerun_ci to already be running before completion.",
                    )
                transition_plans = (
                    CITransitionPlan(
                        task_id=rerun_task.task_id,
                        task_type=rerun_task.task_type,
                        target_status="completed",
                        reason="CI rerun passed.",
                    ),
                )

            return CIHandlingPlan(
                graph_id=graph_id,
                ci_status="passed",
                graph_status="active",
                dispatch_ready_tasks=True,
                metadata_updates=metadata_updates,
                transition_plans=transition_plans,
            )

        ci_status = "failed" if event.event_type == "ci_failed" else event.event_type
        system_alerts: list[dict[str, Any]] = []
        if event.event_type in {"coverage_failed", "security_failed"}:
            system_alerts.append(
                {
                    "severity": "critical",
                    "message": f"Graph '{graph_id}' received CI event '{event.event_type}'.",
                    "graph_id": graph_id,
                    "event_type": event.event_type,
                }
            )

        next_retry_count = graph.retry_count + 1
        if next_retry_count > graph.max_retry_limit:
            task_id = str(event.payload.get("task_id") or f"{graph_id}:ci")
            system_alerts.append(
                {
                    "severity": "critical",
                    "message": f"CI retry limit exceeded after '{event.event_type}'.",
                    "graph_id": graph_id,
                    "task_id": task_id,
                    "event_type": event.event_type,
                }
            )
            return CIHandlingPlan(
                graph_id=graph_id,
                ci_status=ci_status,
                graph_status="requires_human_attention",
                dispatch_ready_tasks=False,
                metadata_updates=metadata_updates,
                block_ci_gated_tasks=True,
                increment_retry=True,
                system_alerts=tuple(system_alerts),
                reason=f"CI retry limit exceeded after '{event.event_type}'.",
            )

        fix_task, rerun_task = self.builder.build_fix_loop(graph, event)
        metadata_updates.update(
            {
                "last_fix_task_id": fix_task.task_id,
                "last_rerun_ci_task_id": rerun_task.task_id,
            }
        )
        return CIHandlingPlan(
            graph_id=graph_id,
            ci_status=ci_status,
            graph_status="blocked",
            dispatch_ready_tasks=True,
            metadata_updates=metadata_updates,
            block_ci_gated_tasks=True,
            increment_retry=True,
            new_tasks=(fix_task, rerun_task),
            system_alerts=tuple(system_alerts),
        )

    @staticmethod
    def _invalid_plan(
        *,
        graph_id: str,
        ci_status: str,
        metadata_updates: dict[str, Any],
        reason: str,
    ) -> CIHandlingPlan:
        return CIHandlingPlan(
            graph_id=graph_id,
            ci_status=ci_status,
            dispatch_ready_tasks=False,
            metadata_updates=metadata_updates,
            valid=False,
            reason=reason,
        )

    @staticmethod
    def _find_last_fix_loop_task(
        graph: TaskGraph,
        metadata_key: str,
        expected_task_type: str,
    ) -> TaskNode | None:
        task_id = graph.metadata.get(metadata_key)
        if not task_id:
            return None
        task = graph.tasks.get(str(task_id))
        if task is None or task.task_type != expected_task_type:
            return None
        return task

    @staticmethod
    def _resolve_graph_id(event: AgentEvent) -> str:
        graph_id = event.payload.get("graph_id")
        if not graph_id:
            raise KeyError("CI event payload is missing graph_id.")
        return str(graph_id)
