from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from workspace.event_bus import (
    SCHEDULER_STREAMS,
    SYSTEM_EVENT_STREAM,
    AgentEvent,
    AgentEventConsumer,
    RedisStreamBus,
    StreamName,
    StreamEventRecord,
    build_audit_payload,
)
from workspace.scheduler.ci_handler import CIEventHandler, CIHandlingPlan
from workspace.scheduler.dag_builder import DagBuilder, TaskGraph, TaskNode
from workspace.scheduler.dag_store import RedisDagStore
from workspace.scheduler.dispatcher import TaskDispatcher
from workspace.scheduler.guardrail_enforcer import GuardrailDecision, GuardrailEnforcer

SCHEDULER_INPUT_EVENTS: tuple[str, ...] = (
    "issue_created",
    "task_graph_created",
    "task_started",
    "task_completed",
    "task_failed",
    "code_generated",
    "ci_started",
    "ci_failed",
    "ci_passed",
    "coverage_failed",
    "security_failed",
)


@dataclass
class SchedulerService:
    """Stateless Redis-backed scheduler that orchestrates tasks through events only."""

    bus: RedisStreamBus
    store: RedisDagStore
    builder: DagBuilder
    dispatcher: TaskDispatcher
    ci_handler: CIEventHandler
    guardrails: GuardrailEnforcer
    group_name: str = "scheduler-group"
    consumer_name: str = "scheduler-service"
    subscribed_streams: tuple[StreamName, ...] = SCHEDULER_STREAMS
    max_retry_limit: int = 2
    _consumer: AgentEventConsumer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._consumer = AgentEventConsumer.build_default(bus=self.bus, consumer_role="scheduler")
        self._consumer.group_name = self.group_name
        self._consumer.consumer_name = self.consumer_name

    @classmethod
    def build_default(
        cls,
        *,
        rules_root: Path | None = None,
        max_retry_limit: int = 2,
    ) -> "SchedulerService":
        bus = RedisStreamBus()
        store = RedisDagStore(bus=bus)
        guardrails = GuardrailEnforcer(rules_root=rules_root)
        builder = DagBuilder()
        dispatcher = TaskDispatcher(bus=bus, store=store, guardrails=guardrails)
        ci_handler = CIEventHandler(builder=builder)
        return cls(
            bus=bus,
            store=store,
            builder=builder,
            dispatcher=dispatcher,
            ci_handler=ci_handler,
            guardrails=guardrails,
            max_retry_limit=max_retry_limit,
        )

    def describe(self) -> dict[str, Any]:
        return {
            "service": "scheduler",
            "phase": "implementation",
            "group_name": self.group_name,
            "consumer_name": self.consumer_name,
            "subscribed_streams": list(self.subscribed_streams),
            "input_events": list(SCHEDULER_INPUT_EVENTS),
            "max_retry_limit": self.max_retry_limit,
            "stateless": True,
            "dag_backend": "redis",
            "ci_source_of_truth": True,
            "direct_agent_calls": False,
            "audit_event_type": "audit_log",
            "idempotent_event_processing": True,
        }

    def observability_snapshot(self) -> dict[str, Any]:
        try:
            return {
                **self.store.load_metrics_snapshot(),
                "processed_event_count": self.store.processed_event_count(),
                "connection_error": None,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "metrics": {},
                "throughput": {},
                "processed_event_count": 0,
                "connection_error": str(exc),
            }

    def ensure_groups(self) -> None:
        self.bus.ensure_consumer_groups(self.subscribed_streams, self.group_name, start_id="0")

    def run_once(self, *, count: int = 20, block_ms: int = 1_000) -> list[dict[str, Any]]:
        self.ensure_groups()
        records = self.bus.read_group(
            self.group_name,
            self.consumer_name,
            {stream: ">" for stream in self.subscribed_streams},
            count=count,
            block_ms=block_ms,
        )

        handled: list[dict[str, Any]] = []
        for record in records:
            try:
                outcome = self.handle_record(record)
            except Exception as exc:  # noqa: BLE001
                outcome = {
                    "status": "error",
                    "error": str(exc),
                    "event_type": record.event.event_type,
                    "graph_id": record.event.payload.get("graph_id"),
                }
                self._publish_system_alert(
                    record.event,
                    message=f"Scheduler failed while handling '{record.event.event_type}': {exc}",
                    severity="critical",
                    extra_payload={"stream": record.stream, "redis_id": record.event_id},
                )
                self._publish_audit_log(
                    record.event,
                    reason=f"Scheduler raised an exception while handling '{record.event.event_type}': {exc}",
                    category="scheduler",
                    result="error",
                    graph_id=str(record.event.payload.get("graph_id") or ""),
                    task_id=str(record.event.payload.get("task_id") or ""),
                )
            finally:
                self.bus.acknowledge(record.stream, self.group_name, record.event_id)

            handled.append(
                {
                    "stream": record.stream,
                    "event_id": record.event_id,
                    "event_type": record.event.event_type,
                    "handler_result": outcome,
                }
            )

        return handled

    def handle_record(self, record: StreamEventRecord) -> dict[str, Any]:
        event = record.event
        if self.store.has_processed_event(event.event_id):
            self._publish_audit_log(
                event,
                reason=f"Duplicate event '{event.event_id}' ignored before state mutation.",
                category="duplicate",
                result="ignored",
            )
            return {
                "status": "duplicate_ignored",
                "graph_id": event.payload.get("graph_id"),
                "task_id": event.payload.get("task_id"),
                "event_id": event.event_id,
            }

        outcome = self._handle_event(record)
        self.store.mark_event_processed(event.event_id)
        return outcome

    def _handle_event(self, record: StreamEventRecord) -> dict[str, Any]:
        event = record.event
        if event.event_type not in SCHEDULER_INPUT_EVENTS:
            return {
                "status": "ignored",
                "reason": "unsupported_event_type",
                "event_type": event.event_type,
            }

        if event.event_type == "issue_created":
            graph = self.builder.build_from_issue(event, max_retry_limit=self.max_retry_limit)
            self.store.save_graph(graph)
            self._record_task_creation(graph.tasks.values())
            readiness = self._refresh_releasable_tasks(graph.graph_id, event=event)
            dispatched = self._finalize_dispatch_results(
                graph.graph_id,
                self.dispatcher.dispatch_ready_tasks(graph.graph_id),
                event=event,
            )
            return {
                "status": "graph_created",
                "graph_id": graph.graph_id,
                "task_count": len(graph.tasks),
                "ready_updates": readiness,
                "dispatched": dispatched,
            }

        if event.event_type == "task_graph_created":
            graph = self.builder.build_from_task_graph(event)
            self.store.save_graph(graph)
            self._record_task_creation(graph.tasks.values())
            readiness = self._refresh_releasable_tasks(graph.graph_id, event=event)
            dispatched = self._finalize_dispatch_results(
                graph.graph_id,
                self.dispatcher.dispatch_ready_tasks(graph.graph_id),
                event=event,
            )
            return {
                "status": "graph_loaded",
                "graph_id": graph.graph_id,
                "task_count": len(graph.tasks),
                "ready_updates": readiness,
                "dispatched": dispatched,
            }

        if event.event_type in {"ci_started", "ci_failed", "ci_passed", "coverage_failed", "security_failed"}:
            graph_id = str(event.payload["graph_id"])
            graph = self.store.load_graph(graph_id)
            plan = self.ci_handler.handle(event, graph)
            return self._apply_ci_plan(event, graph, plan)

        task = self._resolve_task_for_event(event)
        graph = self.store.load_graph(task.graph_id)

        source_decision = self.guardrails.validate_result_source(task, event, graph)
        if not source_decision.allowed:
            if task.assigned_agent == "system":
                return self._handle_trusted_source_violation(task, event, source_decision)
            return self._handle_guardrail_block(task, graph, event, source_decision)

        if event.event_type == "task_started":
            updated_task, violations = self._transition_task(
                task,
                "running",
                graph=graph,
                event=event,
                validation_event=event,
                reason="Task entered running state.",
                category="transition",
            )
            if violations:
                return self._handle_transition_violation(task, event, violations)
            assert updated_task is not None
            self._persist_result_metadata(updated_task.task_id, event)
            return {
                "status": "task_running",
                "graph_id": updated_task.graph_id,
                "task_id": updated_task.task_id,
            }

        decision = self.guardrails.validate_result(task, event)
        if not decision.allowed:
            return self._handle_guardrail_block(task, graph, event, decision)

        if event.event_type in {"task_completed", "code_generated"}:
            completed_task, violations = self._transition_task(
                task,
                "completed",
                graph=graph,
                event=event,
                validation_event=event,
                reason=f"Accepted {event.event_type} result.",
                category="transition",
            )
            if violations:
                return self._handle_transition_violation(task, event, violations)
            assert completed_task is not None
            self._persist_result_metadata(completed_task.task_id, event)
            self._apply_task_completion_side_effects(completed_task, event)
            readiness = self._refresh_releasable_tasks(completed_task.graph_id, event=event)
            dispatched = self._finalize_dispatch_results(
                completed_task.graph_id,
                self.dispatcher.dispatch_ready_tasks(completed_task.graph_id),
                event=event,
            )
            return {
                "status": "task_completed",
                "graph_id": completed_task.graph_id,
                "task_id": completed_task.task_id,
                "ready_updates": readiness,
                "dispatched": dispatched,
            }

        failed_task, violations = self._transition_task(
            task,
            "failed",
            graph=graph,
            event=event,
            validation_event=event,
            reason=f"Accepted {event.event_type} result.",
            category="transition",
        )
        if violations:
            return self._handle_transition_violation(task, event, violations)
        assert failed_task is not None

        if task.assigned_agent == "reviewer":
            self._persist_result_metadata(failed_task.task_id, event)
            self.store.set_graph_status(task.graph_id, "blocked")
            self.store.update_graph_metadata(task.graph_id, {"review_status": "blocked"})
            self._publish_system_alert(
                event,
                message=f"Reviewer blocked progression for graph '{task.graph_id}'.",
                severity="warning",
                extra_payload={"task_id": task.task_id},
            )
            self._publish_audit_log(
                event,
                graph_id=task.graph_id,
                task_id=task.task_id,
                task_type=task.task_type,
                previous_status=task.status,
                next_status=failed_task.status,
                reason="Reviewer blocked progression.",
                category="review",
                result="blocked",
            )
            return {
                "status": "review_blocked",
                "graph_id": task.graph_id,
                "task_id": task.task_id,
            }

        retry_count = self.store.increment_task_retry(task.task_id)
        self._persist_result_metadata(failed_task.task_id, event)
        if retry_count > self.max_retry_limit:
            reason = event.payload.get("reason") or f"Retry limit exceeded for task '{task.task_id}'."
            self.store.record_dead_letter(task.graph_id, task.task_id, str(reason))
            self.store.set_graph_status(task.graph_id, "requires_human_attention")
            self._publish_system_alert(
                event,
                message=str(reason),
                severity="critical",
                extra_payload={"task_id": task.task_id, "retry_count": retry_count},
            )
            self._publish_audit_log(
                event,
                graph_id=task.graph_id,
                task_id=task.task_id,
                task_type=task.task_type,
                previous_status=task.status,
                next_status=failed_task.status,
                reason=str(reason),
                category="retry",
                result="dead_lettered",
            )
            return {
                "status": "task_dead_lettered",
                "graph_id": task.graph_id,
                "task_id": task.task_id,
                "retry_count": retry_count,
            }

        retried_task, retry_violations = self._transition_task(
            failed_task,
            "ready",
            graph=self.store.load_graph(task.graph_id),
            event=event,
            validation_event=None,
            reason="Task re-queued for retry.",
            category="retry",
        )
        if retry_violations:
            return self._handle_transition_violation(failed_task, event, retry_violations)
        assert retried_task is not None

        readiness = self._refresh_releasable_tasks(retried_task.graph_id, event=event)
        dispatched = self._finalize_dispatch_results(
            retried_task.graph_id,
            self.dispatcher.dispatch_ready_tasks(retried_task.graph_id),
            event=event,
        )
        return {
            "status": "task_retried",
            "graph_id": retried_task.graph_id,
            "task_id": retried_task.task_id,
            "retry_count": retry_count,
            "ready_updates": readiness,
            "dispatched": dispatched,
        }

    def _apply_ci_plan(
        self,
        event: AgentEvent,
        graph: TaskGraph,
        plan: CIHandlingPlan,
    ) -> dict[str, Any]:
        if event.event_type in {"ci_failed", "coverage_failed", "security_failed"}:
            self.store.increment_metric("ci_failures")
        self.store.update_graph_metadata(plan.graph_id, plan.metadata_updates)
        self._publish_ci_alerts(event, plan)

        if not plan.valid:
            reason = plan.reason or "Invalid CI ordering."
            self._publish_system_alert(
                event,
                message=reason,
                severity="warning",
                extra_payload={"graph_id": plan.graph_id},
            )
            self._publish_audit_log(
                event,
                graph_id=plan.graph_id,
                reason=reason,
                category="ci",
                result="rejected",
            )
            return {
                "status": "ci_invalid_ordering",
                "graph_id": plan.graph_id,
                "ci_status": graph.ci_status,
                "reason": reason,
            }

        retry_count = graph.retry_count
        if plan.increment_retry:
            retry_count = self.store.increment_graph_retry(plan.graph_id)

        if plan.new_tasks:
            current_graph = self.store.load_graph(plan.graph_id)
            updated_graph = type(current_graph)(
                graph_id=current_graph.graph_id,
                correlation_id=current_graph.correlation_id,
                created_at=current_graph.created_at,
                updated_at=self.builder.utcnow(),
                status=current_graph.status,
                ci_status=current_graph.ci_status,
                max_retry_limit=current_graph.max_retry_limit,
                retry_count=retry_count,
                tasks={**current_graph.tasks, **{task.task_id: task for task in plan.new_tasks}},
                metadata={**current_graph.metadata, **plan.metadata_updates},
            )
            self.store.save_graph(updated_graph)
            self._record_task_creation(plan.new_tasks)
        else:
            if plan.increment_retry:
                current_graph = self.store.load_graph(plan.graph_id)
                updated_graph = type(current_graph)(
                    graph_id=current_graph.graph_id,
                    correlation_id=current_graph.correlation_id,
                    created_at=current_graph.created_at,
                    updated_at=self.builder.utcnow(),
                    status=current_graph.status,
                    ci_status=current_graph.ci_status,
                    max_retry_limit=current_graph.max_retry_limit,
                    retry_count=retry_count,
                    tasks=current_graph.tasks,
                    metadata={**current_graph.metadata, **plan.metadata_updates},
                )
                self.store.save_graph(updated_graph)

        self.store.update_graph_ci_status(plan.graph_id, plan.ci_status)

        graph_for_transitions = self.store.load_graph(plan.graph_id)
        transition_outcomes: list[dict[str, Any]] = []
        if plan.block_ci_gated_tasks:
            transition_outcomes.extend(self._block_ci_gated_tasks(graph_for_transitions, event))
            graph_for_transitions = self.store.load_graph(plan.graph_id)

        for transition in plan.transition_plans:
            task = self.store.load_task(transition.task_id)
            updated_task, violations = self._transition_task(
                task,
                transition.target_status,
                graph=graph_for_transitions,
                event=event,
                validation_event=None,
                reason=transition.reason,
                category="ci",
            )
            if violations:
                return self._handle_transition_violation(task, event, violations)
            assert updated_task is not None
            transition_outcomes.append(
                {
                    "task_id": transition.task_id,
                    "task_type": transition.task_type,
                    "status": updated_task.status,
                }
            )
            graph_for_transitions = self.store.load_graph(plan.graph_id)

        if plan.reason and plan.graph_status == "requires_human_attention":
            task_id = str(event.payload.get("task_id") or f"{plan.graph_id}:ci")
            self.store.record_dead_letter(plan.graph_id, task_id, plan.reason)

        desired_graph_status = self._resolve_graph_status_for_ci(
            self.store.load_graph(plan.graph_id),
            desired_status=plan.graph_status,
        )
        if desired_graph_status is not None:
            self.store.set_graph_status(plan.graph_id, desired_graph_status)

        self._publish_audit_log(
            event,
            graph_id=plan.graph_id,
            reason=plan.reason or f"Handled CI event '{event.event_type}'.",
            category="ci",
            result="accepted",
            next_status=plan.ci_status,
        )

        readiness = self._refresh_releasable_tasks(plan.graph_id, event=event)
        dispatched = []
        if plan.dispatch_ready_tasks:
            dispatched = self._finalize_dispatch_results(
                plan.graph_id,
                self.dispatcher.dispatch_ready_tasks(plan.graph_id),
                event=event,
            )

        status = "ci_handled"
        if desired_graph_status == "requires_human_attention":
            status = "ci_dead_lettered"
        return {
            "status": status,
            "graph_id": plan.graph_id,
            "ci_status": plan.ci_status,
            "retry_count": retry_count,
            "new_tasks": [task.task_id for task in plan.new_tasks],
            "transitions": transition_outcomes,
            "ready_updates": readiness,
            "dispatched": dispatched,
        }

    def _apply_task_completion_side_effects(self, task: TaskNode, event: AgentEvent) -> None:
        if task.task_type == "human_approval_gate":
            approval_source = str(event.payload.get("approval_source") or "").strip().lower()
            approval_status = str(event.payload.get("approval_status") or "approved").strip().lower()
            updates = {
                "human_approval_status": approval_status,
                "human_approval_source": approval_source,
            }
            approval_actor = str(event.payload.get("approval_actor") or "").strip()
            if approval_actor:
                updates["human_approval_actor"] = approval_actor
            self.store.update_graph_metadata(task.graph_id, updates)
            if approval_status != "approved":
                self.store.set_graph_status(task.graph_id, "blocked")
                self._publish_system_alert(
                    event,
                    message=(
                        f"Human approval gate for graph '{task.graph_id}' finished with "
                        f"status '{approval_status}'."
                    ),
                    severity="warning",
                    extra_payload={"task_id": task.task_id, "approval_status": approval_status},
                )
                self._publish_audit_log(
                    event,
                    graph_id=task.graph_id,
                    task_id=task.task_id,
                    task_type=task.task_type,
                    previous_status="running",
                    next_status=task.status,
                    reason=f"Human approval returned '{approval_status}'.",
                    category="merge_gate",
                    result="blocked",
                )
        elif task.task_type == "merge_task":
            self.store.set_graph_status(task.graph_id, "completed")
            self.store.update_graph_metadata(task.graph_id, {"merged_at": event.timestamp})

    def _persist_result_metadata(self, task_id: str, event: AgentEvent) -> None:
        self.store.set_task_payload_field(task_id, "last_result_event", event.to_event_dict())
        self.store.set_task_payload_field(task_id, "last_result_type", event.event_type)

    def _refresh_releasable_tasks(
        self,
        graph_id: str,
        *,
        event: AgentEvent,
    ) -> list[dict[str, Any]]:
        graph = self.store.load_graph(graph_id)
        updates: list[dict[str, Any]] = []

        for task in sorted(graph.tasks.values(), key=lambda item: (item.created_at, item.task_id)):
            if task.status in {"completed", "running", "failed", "cancelled"}:
                continue

            dependencies_completed = all(
                graph.tasks[dependency_id].status == "completed"
                for dependency_id in task.dependencies
                if dependency_id in graph.tasks
            )
            desired_status = task.status
            if not dependencies_completed:
                desired_status = "pending"
            elif self._should_block_task(task, graph):
                desired_status = "blocked"
            else:
                desired_status = "ready"

            if desired_status != task.status:
                updated_task, violations = self._transition_task(
                    task,
                    desired_status,
                    graph=graph,
                    event=event,
                    validation_event=None,
                    reason="Scheduler refreshed task readiness.",
                    category="transition",
                )
                if violations:
                    self._publish_system_alert(
                        event,
                        message=self._format_violations(violations),
                        severity="critical",
                        extra_payload={"task_id": task.task_id, "target_status": desired_status},
                    )
                    self.store.set_graph_status(graph.graph_id, "requires_human_attention")
                    continue
                assert updated_task is not None

                if updated_task.task_type == "merge_task" and updated_task.status == "blocked":
                    self._publish_merge_gate_block(
                        event,
                        task=updated_task,
                        reason="Merge is blocked until recorded human approval is present.",
                        previous_status=task.status,
                    )

                updates.append(
                    {
                        "task_id": updated_task.task_id,
                        "from": task.status,
                        "to": updated_task.status,
                    }
                )
                graph = self.store.load_graph(graph_id)

        return updates

    def _should_block_task(self, task: TaskNode, graph: TaskGraph) -> bool:
        if task.guardrail_policy.get("requires_ci_pass") and graph.ci_status != "passed":
            return True
        if task.task_type == "merge_task" and graph.metadata.get("human_approval_status") != "approved":
            return True
        if graph.ci_status in {"failed", "coverage_failed", "security_failed"} and task.task_type not in {
            "fix_task",
            "rerun_ci",
        }:
            if task.task_type in {"review_task", "human_approval_gate", "merge_task"}:
                return True
        return False

    def _block_ci_gated_tasks(self, graph: TaskGraph, event: AgentEvent) -> list[dict[str, Any]]:
        updates: list[dict[str, Any]] = []
        for task in graph.tasks.values():
            if task.task_type in {"fix_task", "rerun_ci"}:
                continue
            if not task.guardrail_policy.get("requires_ci_pass"):
                continue
            if task.status in {"completed", "cancelled", "failed", "blocked"}:
                continue

            updated_task, violations = self._transition_task(
                task,
                "blocked",
                graph=graph,
                event=event,
                validation_event=None,
                reason=f"Blocked by CI status '{graph.ci_status}'.",
                category="ci",
            )
            if violations:
                raise RuntimeError(self._format_violations(violations))
            assert updated_task is not None
            updates.append({"task_id": updated_task.task_id, "status": updated_task.status})
        return updates

    def _resolve_task_for_event(self, event: AgentEvent) -> TaskNode:
        payload = event.payload
        raw_task_id = str(payload.get("task_id") or "").strip()
        if raw_task_id:
            try:
                return self.store.load_task(raw_task_id)
            except KeyError:
                pass

        graph_id = str(payload.get("graph_id") or event.correlation_id)
        graph = self.store.load_graph(graph_id)
        requested_task_type = payload.get("task_type")

        candidates = list(graph.tasks.values())
        if requested_task_type:
            candidates = [task for task in candidates if task.task_type == requested_task_type]
        elif event.source != "system":
            candidates = [task for task in candidates if task.assigned_agent == event.source]

        candidates = sorted(candidates, key=lambda task: self._task_match_priority(task, event))
        if not candidates:
            raise KeyError(f"Unable to resolve task for event '{event.event_type}' in graph '{graph_id}'.")
        return candidates[0]

    def _task_match_priority(self, task: TaskNode, event: AgentEvent) -> tuple[int, int, str, str]:
        status_order = {
            "running": 0,
            "ready": 1,
            "blocked": 2,
            "pending": 3,
            "failed": 4,
            "completed": 5,
            "cancelled": 6,
        }
        task_type_order = {
            "planner": {"plan_task": 0},
            "coder": {"fix_task": 0, "implement_task": 1},
            "tester": {"test_task": 0},
            "reviewer": {"review_task": 0},
            "system": {"human_approval_gate": 0, "merge_task": 1, "rerun_ci": 2},
        }
        role_priority = task_type_order.get(event.source, {})
        return (
            status_order.get(task.status, 99),
            role_priority.get(task.task_type, 99),
            task.updated_at,
            task.task_id,
        )

    def _finalize_dispatch_results(
        self,
        graph_id: str,
        dispatched: list[dict[str, Any]],
        *,
        event: AgentEvent,
    ) -> list[dict[str, Any]]:
        finalized: list[dict[str, Any]] = []
        for item in dispatched:
            task = self.store.load_task(str(item["task_id"]))
            graph = self.store.load_graph(graph_id)

            if item["dispatched"]:
                updated_task, violations = self._transition_task(
                    task,
                    "running",
                    graph=graph,
                    event=event,
                    validation_event=None,
                    reason=f"Task dispatched to '{task.assigned_agent}'.",
                    category="dispatch",
                )
                if violations:
                    finalized.append(self._handle_transition_violation(task, event, violations))
                    continue
                assert updated_task is not None
                finalized.append({**item, "status": updated_task.status})
                continue

            updated_task, violations = self._transition_task(
                task,
                "blocked",
                graph=graph,
                event=event,
                validation_event=None,
                reason="Dispatch blocked by guardrails.",
                category="dispatch",
            )
            if violations:
                finalized.append(self._handle_transition_violation(task, event, violations))
                continue
            assert updated_task is not None

            if task.task_type == "merge_task":
                self._publish_merge_gate_block(
                    event,
                    task=updated_task,
                    reason=self._format_violation_dicts(item.get("violations", [])),
                    previous_status=task.status,
                )

            finalized.append({**item, "status": updated_task.status})

        return finalized

    def _publish_ci_alerts(self, event: AgentEvent, plan: CIHandlingPlan) -> None:
        for alert in plan.system_alerts:
            self._publish_system_alert(
                event,
                message=str(alert.get("message", "Critical CI alert.")),
                severity=str(alert.get("severity", "critical")),
                extra_payload={key: value for key, value in alert.items() if key not in {"message", "severity"}},
            )

    def _publish_system_alert(
        self,
        event: AgentEvent,
        *,
        message: str,
        severity: str,
        extra_payload: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "severity": severity,
            "message": message,
            "graph_id": event.payload.get("graph_id"),
            **(extra_payload or {}),
        }
        self.bus.publish(
            SYSTEM_EVENT_STREAM,
            AgentEvent.create(
                event_type="system_alert",
                source="scheduler",
                correlation_id=event.correlation_id,
                payload=payload,
            ),
        )

    def _publish_audit_log(
        self,
        event: AgentEvent,
        *,
        reason: str,
        category: str,
        result: str,
        graph_id: str | None = None,
        task_id: str | None = None,
        task_type: str | None = None,
        previous_status: str | None = None,
        next_status: str | None = None,
    ) -> None:
        payload = build_audit_payload(
            event,
            graph_id=graph_id,
            task_id=task_id,
            task_type=task_type,
            previous_status=previous_status,
            next_status=next_status,
            reason=reason,
            category=category,
            result=result,
        )
        self.bus.publish(
            SYSTEM_EVENT_STREAM,
            AgentEvent.create(
                event_type="audit_log",
                source="scheduler",
                correlation_id=event.correlation_id,
                payload=payload,
            ),
        )

    def _publish_merge_gate_block(
        self,
        event: AgentEvent,
        *,
        task: TaskNode,
        reason: str,
        previous_status: str,
    ) -> None:
        self.store.increment_metric("merge_blocks")
        self._publish_system_alert(
            event,
            message=reason,
            severity="warning",
            extra_payload={"task_id": task.task_id, "task_type": task.task_type},
        )
        self._publish_audit_log(
            event,
            graph_id=task.graph_id,
            task_id=task.task_id,
            task_type=task.task_type,
            previous_status=previous_status,
            next_status=task.status,
            reason=reason,
            category="merge_gate",
            result="blocked",
        )

    def _transition_task(
        self,
        task: TaskNode,
        target_status: str,
        *,
        graph: TaskGraph,
        event: AgentEvent | None = None,
        validation_event: AgentEvent | None = None,
        reason: str,
        category: str,
    ) -> tuple[TaskNode | None, GuardrailDecision | None]:
        if task.status == target_status:
            return task, None

        decision = self.guardrails.validate_transition(
            task,
            target_status=target_status,  # type: ignore[arg-type]
            graph=graph,
            event=validation_event,
        )
        if not decision.allowed:
            if event is not None:
                self._publish_audit_log(
                    event,
                    graph_id=task.graph_id,
                    task_id=task.task_id,
                    task_type=task.task_type,
                    previous_status=task.status,
                    next_status=target_status,
                    reason=self._format_violations(decision),
                    category=category,
                    result="rejected",
                )
            return None, decision

        updated_task = self.store.update_task_status(task.task_id, target_status)
        self.store.increment_throughput(updated_task.status, updated_task.task_type)
        if updated_task.status == "blocked":
            self.store.increment_metric("tasks_blocked")

        if event is not None:
            self._publish_audit_log(
                event,
                graph_id=task.graph_id,
                task_id=task.task_id,
                task_type=task.task_type,
                previous_status=task.status,
                next_status=updated_task.status,
                reason=reason,
                category=category,
                result="accepted",
            )
        return updated_task, None

    def _handle_transition_violation(
        self,
        task: TaskNode,
        event: AgentEvent,
        decision: GuardrailDecision,
    ) -> dict[str, Any]:
        reason = self._format_violations(decision)
        self.store.record_dead_letter(task.graph_id, task.task_id, reason)
        self.store.set_graph_status(task.graph_id, "requires_human_attention")
        self._publish_system_alert(
            event,
            message=reason,
            severity="critical",
            extra_payload={"task_id": task.task_id, "violations": decision.to_dict()["violations"]},
        )
        return {
            "status": "invalid_transition",
            "graph_id": task.graph_id,
            "task_id": task.task_id,
            "violations": decision.to_dict()["violations"],
        }

    def _handle_trusted_source_violation(
        self,
        task: TaskNode,
        event: AgentEvent,
        decision: GuardrailDecision,
    ) -> dict[str, Any]:
        reason = self._format_violations(decision)
        self._publish_system_alert(
            event,
            message=reason,
            severity="warning",
            extra_payload={"task_id": task.task_id, "violations": decision.to_dict()["violations"]},
        )
        if task.task_type == "merge_task":
            self.store.increment_metric("merge_blocks")
        self._publish_audit_log(
            event,
            graph_id=task.graph_id,
            task_id=task.task_id,
            task_type=task.task_type,
            previous_status=task.status,
            next_status=task.status,
            reason=reason,
            category="trusted_source",
            result="rejected",
        )
        return {
            "status": "trusted_source_rejected",
            "graph_id": task.graph_id,
            "task_id": task.task_id,
            "violations": decision.to_dict()["violations"],
        }

    def _handle_guardrail_block(
        self,
        task: TaskNode,
        graph: TaskGraph,
        event: AgentEvent,
        decision: GuardrailDecision,
    ) -> dict[str, Any]:
        failure_event = AgentEvent.create(
            event_type="task_failed",
            source="scheduler",
            correlation_id=event.correlation_id,
            payload=event.payload,
        )
        updated_task, transition_violations = self._transition_task(
            task,
            "failed",
            graph=graph,
            event=event,
            validation_event=failure_event,
            reason=self._format_violations(decision),
            category="guardrail",
        )
        if transition_violations:
            return self._handle_transition_violation(task, event, transition_violations)
        assert updated_task is not None

        reason = self._format_violations(decision)
        self.store.record_dead_letter(task.graph_id, task.task_id, reason)
        self.store.set_graph_status(task.graph_id, "requires_human_attention")
        self._publish_system_alert(
            event,
            message=reason,
            severity="critical",
            extra_payload={"task_id": task.task_id, "violations": decision.to_dict()["violations"]},
        )
        self._publish_audit_log(
            event,
            graph_id=task.graph_id,
            task_id=task.task_id,
            task_type=task.task_type,
            previous_status=task.status,
            next_status=updated_task.status,
            reason=reason,
            category="guardrail",
            result="rejected",
        )
        return {
            "status": "guardrail_blocked",
            "graph_id": task.graph_id,
            "task_id": task.task_id,
            "violations": decision.to_dict()["violations"],
        }

    def _record_task_creation(self, tasks: Any) -> None:
        items = list(tasks)
        if not items:
            return
        self.store.increment_metric("tasks_created", amount=len(items))
        for task in items:
            self.store.increment_throughput("created", task.task_type)

    def _resolve_graph_status_for_ci(self, graph: TaskGraph, *, desired_status: str | None) -> str | None:
        if desired_status is None:
            return None
        if desired_status != "active":
            return desired_status
        if graph.status in {"requires_human_attention", "completed"}:
            return graph.status
        if graph.metadata.get("review_status") == "blocked":
            return "blocked"
        approval_status = str(graph.metadata.get("human_approval_status") or "").strip().lower()
        if approval_status and approval_status != "approved":
            return "blocked"
        return "active"

    @staticmethod
    def _format_violations(decision: GuardrailDecision) -> str:
        messages = [violation["message"] for violation in decision.to_dict()["violations"]]
        return "; ".join(messages) or "Guardrail validation failed."

    @staticmethod
    def _format_violation_dicts(violations: list[dict[str, Any]]) -> str:
        messages = [str(violation.get("message", "")) for violation in violations]
        return "; ".join(message for message in messages if message) or "Guardrail validation failed."
