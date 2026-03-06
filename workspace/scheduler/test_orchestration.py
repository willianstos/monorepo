from __future__ import annotations

import unittest
from pathlib import Path

from workspace.event_bus import (
    AGENT_RESULT_STREAM,
    AGENT_TASK_STREAM,
    CI_EVENT_STREAM,
    MEMORY_EVENT_STREAM,
    SYSTEM_EVENT_STREAM,
    AgentEvent,
)
from workspace.memory import MemoryRuntimeService
from workspace.scheduler import SchedulerService
from workspace.runtime.assistant_runtime import AssistantRuntime


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.sets: dict[str, set[str]] = {}
        self.strings: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.group_offsets: dict[tuple[str, str], int] = {}

    def xadd(self, *, name: str, fields: dict[str, str], id: str = "*", **_: object) -> str:
        messages = self.streams.setdefault(name, [])
        redis_id = f"{len(messages) + 1}-0" if id == "*" else id
        messages.append((redis_id, dict(fields)))
        return redis_id

    def xread(self, *, streams: dict[str, str], count: int = 10, block: int = 0) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
        del block
        output: list[tuple[str, list[tuple[str, dict[str, str]]]]] = []
        remaining = count
        for stream_name, offset in streams.items():
            messages = self.streams.get(stream_name, [])
            if offset == "$":
                continue
            selected = messages[:remaining]
            if selected:
                output.append((stream_name, selected))
                remaining -= len(selected)
                if remaining <= 0:
                    break
        return output

    def xgroup_create(self, name: str, groupname: str, id: str = "0", mkstream: bool = True) -> None:
        if mkstream:
            self.streams.setdefault(name, [])
        if id == "$":
            self.group_offsets[(groupname, name)] = len(self.streams.get(name, []))
            return
        self.group_offsets.setdefault((groupname, name), 0)

    def xreadgroup(
        self,
        *,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int = 10,
        block: int = 0,
        noack: bool = False,
    ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
        del consumername, block, noack
        output: list[tuple[str, list[tuple[str, dict[str, str]]]]] = []
        remaining = count
        for stream_name, offset in streams.items():
            messages = self.streams.get(stream_name, [])
            if offset == ">":
                start = self.group_offsets.get((groupname, stream_name), 0)
            else:
                start = 0
            selected = messages[start : start + remaining]
            self.group_offsets[(groupname, stream_name)] = start + len(selected)
            if selected:
                output.append((stream_name, selected))
                remaining -= len(selected)
                if remaining <= 0:
                    break
        return output

    def xack(self, stream: str, group_name: str, event_id: str) -> int:
        del stream, group_name, event_id
        return 1

    def ping(self) -> bool:
        return True

    def hset(self, name: str, mapping: dict[str, str]) -> int:
        values = self.hashes.setdefault(name, {})
        values.update({key: str(value) for key, value in mapping.items()})
        return len(mapping)

    def hgetall(self, name: str) -> dict[str, str]:
        return dict(self.hashes.get(name, {}))

    def hincrby(self, name: str, key: str, amount: int) -> int:
        values = self.hashes.setdefault(name, {})
        current = int(values.get(key, "0"))
        current += amount
        values[key] = str(current)
        return current

    def sadd(self, name: str, *values: str) -> int:
        members = self.sets.setdefault(name, set())
        previous_size = len(members)
        members.update(str(value) for value in values)
        return len(members) - previous_size

    def smembers(self, name: str) -> set[str]:
        return set(self.sets.get(name, set()))

    def sismember(self, name: str, value: str) -> bool:
        return str(value) in self.sets.get(name, set())

    def scard(self, name: str) -> int:
        return len(self.sets.get(name, set()))

    def set(self, name: str, value: str) -> bool:
        self.strings[name] = str(value)
        return True

    def get(self, name: str) -> str | None:
        return self.strings.get(name)

    def delete(self, name: str) -> int:
        deleted = 0
        for collection in (self.hashes, self.sets, self.strings, self.lists):
            if name in collection:
                del collection[name]
                deleted += 1
        return deleted

    def rpush(self, name: str, *values: str) -> int:
        bucket = self.lists.setdefault(name, [])
        bucket.extend(str(value) for value in values)
        return len(bucket)

    def lrange(self, name: str, start: int, end: int) -> list[str]:
        values = self.lists.get(name, [])
        if end == -1:
            end = len(values) - 1
        return list(values[start : end + 1])


class SchedulerOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_redis = FakeRedis()
        self.scheduler = SchedulerService.build_default(
            rules_root=Path("guardrails"),
            max_retry_limit=1,
        )
        self.scheduler.bus.client = self.fake_redis
        self.scheduler.ensure_groups()

    def test_issue_created_builds_graph_and_dispatches_plan_task(self) -> None:
        graph_id = "graph-001"
        self.scheduler.bus.publish(
            AGENT_TASK_STREAM,
            AgentEvent.create(
                event_type="issue_created",
                source="planner",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "objective": "Implement scheduler"},
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["handler_result"]["status"], "graph_created")
        graph = self.scheduler.store.load_graph(graph_id)
        plan_task = graph.tasks[f"{graph_id}:plan_task"]
        self.assertEqual(plan_task.status, "running")

        events = self._stream_events(AGENT_TASK_STREAM)
        self.assertEqual([event.event_type for event in events], ["issue_created", "task_created"])
        self.assertEqual(events[-1].payload["task_id"], f"{graph_id}:plan_task")

    def test_task_completion_releases_implement_task(self) -> None:
        graph_id = self._create_graph()
        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="planner",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "task_id": f"{graph_id}:plan_task"},
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        completion = [item for item in results if item["handler_result"]["status"] == "task_completed"]
        self.assertEqual(len(completion), 1)
        graph = self.scheduler.store.load_graph(graph_id)
        self.assertEqual(graph.tasks[f"{graph_id}:plan_task"].status, "completed")
        self.assertEqual(graph.tasks[f"{graph_id}:implement_task"].status, "running")

    def test_ci_failed_creates_fix_loop_and_dispatches_fix_task(self) -> None:
        graph_id = self._create_graph()
        self.scheduler.bus.publish(
            CI_EVENT_STREAM,
            AgentEvent.create(
                event_type="ci_failed",
                source="ci",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "reason": "unit tests failed"},
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        ci_outcomes = [item for item in results if item["handler_result"]["status"] == "ci_handled"]
        self.assertEqual(len(ci_outcomes), 1)
        self.assertEqual(
            ci_outcomes[0]["handler_result"]["new_tasks"],
            [f"{graph_id}:fix_task:1", f"{graph_id}:rerun_ci:1"],
        )
        graph = self.scheduler.store.load_graph(graph_id)
        self.assertEqual(graph.ci_status, "failed")
        self.assertIn(f"{graph_id}:fix_task:1", graph.tasks)
        self.assertIn(f"{graph_id}:rerun_ci:1", graph.tasks)
        self.assertEqual(graph.tasks[f"{graph_id}:fix_task:1"].status, "running")
        self.assertEqual(graph.tasks[f"{graph_id}:rerun_ci:1"].status, "pending")

    def test_task_failure_dead_letters_after_retry_limit(self) -> None:
        graph_id = self._create_graph()
        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="planner",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "task_id": f"{graph_id}:plan_task"},
            ),
        )
        self.scheduler.run_once(count=10, block_ms=0)

        first_failure_event = AgentEvent.create(
            event_type="task_failed",
            source="coder",
            correlation_id="11111111-1111-1111-1111-111111111111",
            payload={"graph_id": graph_id, "task_id": f"{graph_id}:implement_task", "reason": "compile failed"},
        )
        second_failure_event = AgentEvent.create(
            event_type="task_failed",
            source="coder",
            correlation_id="11111111-1111-1111-1111-111111111111",
            payload={"graph_id": graph_id, "task_id": f"{graph_id}:implement_task", "reason": "compile failed"},
        )
        self.scheduler.bus.publish(AGENT_RESULT_STREAM, first_failure_event)
        first_retry = self.scheduler.run_once(count=10, block_ms=0)
        retry_outcomes = [item for item in first_retry if item["handler_result"]["status"] == "task_retried"]
        self.assertEqual(len(retry_outcomes), 1)

        self.scheduler.bus.publish(AGENT_RESULT_STREAM, second_failure_event)
        second_retry = self.scheduler.run_once(count=10, block_ms=0)
        dead_lettered = [item for item in second_retry if item["handler_result"]["status"] == "task_dead_lettered"]
        self.assertEqual(len(dead_lettered), 1)
        graph = self.scheduler.store.load_graph(graph_id)
        self.assertEqual(graph.status, "requires_human_attention")
        self.assertEqual(len(self.fake_redis.lists[self.scheduler.store.dead_letter_key(graph_id)]), 1)
        system_events = self._stream_events(SYSTEM_EVENT_STREAM)
        self.assertTrue(any(event.event_type == "system_alert" for event in system_events))

    def test_invalid_assignment_is_blocked_before_dispatch(self) -> None:
        task = self.scheduler.builder.build_task_node(
            graph_id="graph-invalid-assignment",
            task_id="graph-invalid-assignment:test_task",
            task_type="test_task",
            assigned_agent="coder",
            dependencies=(),
            status="ready",
        )
        graph = self.scheduler.builder.build_from_task_graph(
            AgentEvent.create(
                event_type="task_graph_created",
                source="planner",
                correlation_id="22222222-2222-2222-2222-222222222222",
                payload={
                    "graph_id": "graph-invalid-assignment",
                    "tasks": [task.to_dict()],
                    "ci_status": "passed",
                },
            )
        )
        self.scheduler.store.save_graph(graph)

        trigger_event = AgentEvent.create(
            event_type="task_graph_created",
            source="planner",
            correlation_id="22222222-2222-2222-2222-222222222222",
            payload={"graph_id": graph.graph_id},
        )
        dispatched = self.scheduler._finalize_dispatch_results(
            graph.graph_id,
            self.scheduler.dispatcher.dispatch_ready_tasks(graph.graph_id),
            event=trigger_event,
        )

        self.assertEqual(dispatched[0]["dispatched"], False)
        self.assertEqual(self.scheduler.store.load_task(task.task_id).status, "blocked")
        agent_events = [
            event for event in self._stream_events(AGENT_TASK_STREAM) if event.event_type != "issue_created"
        ]
        self.assertEqual(agent_events, [])

    def test_invalid_transition_is_rejected(self) -> None:
        graph_id = self._create_graph()
        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="coder",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "task_id": f"{graph_id}:implement_task"},
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        violations = [item for item in results if item["handler_result"]["status"] == "invalid_transition"]
        self.assertEqual(len(violations), 1)
        graph = self.scheduler.store.load_graph(graph_id)
        self.assertEqual(graph.status, "requires_human_attention")

    def test_coder_cannot_modify_tests_or_ci(self) -> None:
        graph_id = self._create_graph()
        self._complete_task(graph_id, "plan_task", source="planner")

        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="coder",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={
                    "graph_id": graph_id,
                    "task_id": f"{graph_id}:implement_task",
                    "changed_files": ["tests/test_scheduler.py", ".github/workflows/ci.yml"],
                },
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        blocked = [item for item in results if item["handler_result"]["status"] == "guardrail_blocked"]
        self.assertEqual(len(blocked), 1)
        violations = blocked[0]["handler_result"]["violations"]
        self.assertTrue(any(item["rule"] == "coder_test_boundary" for item in violations))
        self.assertTrue(any(item["rule"] == "coder_ci_boundary" for item in violations))

    def test_tester_may_not_modify_implementation(self) -> None:
        graph_id = self._create_graph()
        self._complete_task(graph_id, "plan_task", source="planner")
        self._complete_task(graph_id, "implement_task", source="coder")

        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="tester",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={
                    "graph_id": graph_id,
                    "task_id": f"{graph_id}:test_task",
                    "changed_files": ["workspace/scheduler/service.py"],
                },
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        blocked = [item for item in results if item["handler_result"]["status"] == "guardrail_blocked"]
        self.assertEqual(len(blocked), 1)
        self.assertTrue(
            any(item["rule"] == "tester_scope" for item in blocked[0]["handler_result"]["violations"])
        )

    def test_reviewer_failure_blocks_progression(self) -> None:
        graph_id = self._create_graph()
        self._complete_task(graph_id, "plan_task", source="planner")
        self._complete_task(graph_id, "implement_task", source="coder")
        self._complete_task(graph_id, "test_task", source="tester")
        self._publish_ci("ci_passed", graph_id)

        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_failed",
                source="reviewer",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "task_id": f"{graph_id}:review_task", "reason": "risk found"},
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        blocked = [item for item in results if item["handler_result"]["status"] == "review_blocked"]
        self.assertEqual(len(blocked), 1)
        graph = self.scheduler.store.load_graph(graph_id)
        self.assertEqual(graph.status, "blocked")
        self.assertEqual(graph.metadata["review_status"], "blocked")

    def test_merge_dispatch_requires_human_approval(self) -> None:
        merge_task = self.scheduler.builder.build_task_node(
            graph_id="graph-merge",
            task_id="graph-merge:merge_task",
            task_type="merge_task",
            assigned_agent="system",
            dependencies=(),
            status="ready",
        )
        graph = self.scheduler.builder.build_from_task_graph(
            AgentEvent.create(
                event_type="task_graph_created",
                source="planner",
                correlation_id="33333333-3333-3333-3333-333333333333",
                payload={
                    "graph_id": "graph-merge",
                    "tasks": [merge_task.to_dict()],
                    "ci_status": "passed",
                },
            )
        )
        self.scheduler.store.save_graph(graph)

        trigger_event = AgentEvent.create(
            event_type="task_graph_created",
            source="planner",
            correlation_id="33333333-3333-3333-3333-333333333333",
            payload={"graph_id": "graph-merge"},
        )
        dispatched = self.scheduler._finalize_dispatch_results(
            "graph-merge",
            self.scheduler.dispatcher.dispatch_ready_tasks("graph-merge"),
            event=trigger_event,
        )

        self.assertEqual(dispatched[0]["dispatched"], False)
        self.assertEqual(self.scheduler.store.load_task("graph-merge:merge_task").status, "blocked")
        system_events = self._stream_events(SYSTEM_EVENT_STREAM)
        self.assertTrue(any(event.event_type == "audit_log" for event in system_events))

    def test_ci_passed_releases_review_task(self) -> None:
        graph_id = self._create_graph()
        self._complete_task(graph_id, "plan_task", source="planner")
        self._complete_task(graph_id, "implement_task", source="coder")
        self._complete_task(graph_id, "test_task", source="tester")

        self._publish_ci("ci_passed", graph_id)

        graph = self.scheduler.store.load_graph(graph_id)
        self.assertEqual(graph.ci_status, "passed")
        self.assertEqual(graph.tasks[f"{graph_id}:review_task"].status, "running")

    def test_runtime_dry_run_reports_guardrails_and_memory_policy(self) -> None:
        runtime = AssistantRuntime(workspace_root=Path("workspace"))

        report = runtime.dry_run_validation()

        self.assertTrue(report["bootstrap_coherent"])
        self.assertTrue(report["memory"]["no_raw_conversation_storage"])
        self.assertEqual(report["guardrails"]["missing_rules"], [])

    def test_scheduler_health_report_surfaces_operator_signals(self) -> None:
        runtime = AssistantRuntime(workspace_root=Path("workspace"))
        runtime.scheduler_service = lambda: self.scheduler  # type: ignore[method-assign]
        self.scheduler.store.increment_metric("merge_blocks")

        report = runtime.scheduler_health_report()

        self.assertEqual(report["status"], "attention_required")
        self.assertEqual(report["summary"]["merge_blocks"], 1)
        self.assertTrue(any("Merge blocks were recorded" in hint for hint in report["operator_hints"]))

    def test_coder_cannot_complete_merge_task(self) -> None:
        graph_id = "graph-merge-result"
        merge_task = self.scheduler.builder.build_task_node(
            graph_id=graph_id,
            task_id=f"{graph_id}:merge_task",
            task_type="merge_task",
            assigned_agent="system",
            dependencies=(),
            status="running",
        )
        graph = self.scheduler.builder.build_from_task_graph(
            AgentEvent.create(
                event_type="task_graph_created",
                source="planner",
                correlation_id="44444444-4444-4444-4444-444444444444",
                payload={
                    "graph_id": graph_id,
                    "tasks": [merge_task.to_dict()],
                    "ci_status": "passed",
                    "human_approval_status": "approved",
                },
            )
        )
        self.scheduler.store.save_graph(graph)
        self.scheduler.store.update_graph_metadata(graph_id, {"human_approval_status": "approved"})

        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="coder",
                correlation_id="44444444-4444-4444-4444-444444444444",
                payload={"graph_id": graph_id, "task_id": merge_task.task_id},
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        rejected = [item for item in results if item["handler_result"]["status"] == "trusted_source_rejected"]
        self.assertEqual(len(rejected), 1)
        self.assertEqual(self.scheduler.store.load_task(merge_task.task_id).status, "running")

    def test_coder_cannot_complete_human_approval_gate(self) -> None:
        graph_id = "graph-approval-result"
        approval_task = self.scheduler.builder.build_task_node(
            graph_id=graph_id,
            task_id=f"{graph_id}:human_approval_gate",
            task_type="human_approval_gate",
            assigned_agent="system",
            dependencies=(),
            status="running",
        )
        graph = self.scheduler.builder.build_from_task_graph(
            AgentEvent.create(
                event_type="task_graph_created",
                source="planner",
                correlation_id="55555555-5555-5555-5555-555555555555",
                payload={
                    "graph_id": graph_id,
                    "tasks": [approval_task.to_dict()],
                    "ci_status": "passed",
                },
            )
        )
        self.scheduler.store.save_graph(graph)

        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="coder",
                correlation_id="55555555-5555-5555-5555-555555555555",
                payload={"graph_id": graph_id, "task_id": approval_task.task_id},
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        rejected = [item for item in results if item["handler_result"]["status"] == "trusted_source_rejected"]
        self.assertEqual(len(rejected), 1)
        self.assertEqual(self.scheduler.store.load_task(approval_task.task_id).status, "running")

    def test_untrusted_source_cannot_complete_rerun_ci(self) -> None:
        graph_id = "graph-rerun-result"
        fix_task = self.scheduler.builder.build_task_node(
            graph_id=graph_id,
            task_id=f"{graph_id}:fix_task:1",
            task_type="fix_task",
            assigned_agent="coder",
            dependencies=(),
            status="completed",
        )
        rerun_task = self.scheduler.builder.build_task_node(
            graph_id=graph_id,
            task_id=f"{graph_id}:rerun_ci:1",
            task_type="rerun_ci",
            assigned_agent="system",
            dependencies=(fix_task.task_id,),
            status="running",
        )
        graph = self.scheduler.builder.build_from_task_graph(
            AgentEvent.create(
                event_type="task_graph_created",
                source="planner",
                correlation_id="66666666-6666-6666-6666-666666666666",
                payload={
                    "graph_id": graph_id,
                    "tasks": [fix_task.to_dict(), rerun_task.to_dict()],
                    "ci_status": "running",
                    "last_fix_task_id": fix_task.task_id,
                    "last_rerun_ci_task_id": rerun_task.task_id,
                },
            )
        )
        self.scheduler.store.save_graph(graph)

        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="reviewer",
                correlation_id="66666666-6666-6666-6666-666666666666",
                payload={"graph_id": graph_id, "task_id": rerun_task.task_id},
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        rejected = [item for item in results if item["handler_result"]["status"] == "trusted_source_rejected"]
        self.assertEqual(len(rejected), 1)
        self.assertEqual(self.scheduler.store.load_task(rerun_task.task_id).status, "running")

    def test_trusted_system_completion_of_human_approval_gate_requires_valid_payload(self) -> None:
        graph_id = "graph-human-approval"
        approval_task = self.scheduler.builder.build_task_node(
            graph_id=graph_id,
            task_id=f"{graph_id}:human_approval_gate",
            task_type="human_approval_gate",
            assigned_agent="system",
            dependencies=(),
            status="running",
        )
        merge_task = self.scheduler.builder.build_task_node(
            graph_id=graph_id,
            task_id=f"{graph_id}:merge_task",
            task_type="merge_task",
            assigned_agent="system",
            dependencies=(approval_task.task_id,),
            status="pending",
        )
        graph = self.scheduler.builder.build_from_task_graph(
            AgentEvent.create(
                event_type="task_graph_created",
                source="planner",
                correlation_id="77777777-7777-7777-7777-777777777777",
                payload={
                    "graph_id": graph_id,
                    "tasks": [approval_task.to_dict(), merge_task.to_dict()],
                    "ci_status": "passed",
                },
            )
        )
        self.scheduler.store.save_graph(graph)

        invalid_event = AgentEvent.create(
            event_type="task_completed",
            source="system",
            correlation_id="77777777-7777-7777-7777-777777777777",
            payload={"graph_id": graph_id, "task_id": approval_task.task_id},
        )
        self.scheduler.bus.publish(AGENT_RESULT_STREAM, invalid_event)
        invalid_results = self.scheduler.run_once(count=10, block_ms=0)
        self.assertEqual(invalid_results[0]["handler_result"]["status"], "trusted_source_rejected")
        self.assertEqual(self.scheduler.store.load_task(approval_task.task_id).status, "running")

        valid_event = AgentEvent.create(
            event_type="task_completed",
            source="system",
            correlation_id="77777777-7777-7777-7777-777777777777",
            payload={
                "graph_id": graph_id,
                "task_id": approval_task.task_id,
                "approval_source": "human",
                "approval_status": "approved",
                "approval_actor": "alice",
            },
        )
        self.scheduler.bus.publish(AGENT_RESULT_STREAM, valid_event)
        valid_results = self.scheduler.run_once(count=10, block_ms=0)

        completed = [item for item in valid_results if item["handler_result"]["status"] == "task_completed"]
        self.assertEqual(len(completed), 1)
        updated_graph = self.scheduler.store.load_graph(graph_id)
        self.assertEqual(updated_graph.metadata["human_approval_status"], "approved")
        self.assertEqual(updated_graph.tasks[merge_task.task_id].status, "running")

    def test_trusted_system_completion_of_merge_task_only_works_after_recorded_approval(self) -> None:
        graph_id = "graph-merge-approval"
        merge_task = self.scheduler.builder.build_task_node(
            graph_id=graph_id,
            task_id=f"{graph_id}:merge_task",
            task_type="merge_task",
            assigned_agent="system",
            dependencies=(),
            status="running",
        )
        graph = self.scheduler.builder.build_from_task_graph(
            AgentEvent.create(
                event_type="task_graph_created",
                source="planner",
                correlation_id="88888888-8888-8888-8888-888888888888",
                payload={
                    "graph_id": graph_id,
                    "tasks": [merge_task.to_dict()],
                    "ci_status": "passed",
                },
            )
        )
        self.scheduler.store.save_graph(graph)

        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="system",
                correlation_id="88888888-8888-8888-8888-888888888888",
                payload={"graph_id": graph_id, "task_id": merge_task.task_id},
            ),
        )
        rejected_results = self.scheduler.run_once(count=10, block_ms=0)
        self.assertEqual(rejected_results[0]["handler_result"]["status"], "trusted_source_rejected")
        self.assertEqual(self.scheduler.store.load_task(merge_task.task_id).status, "running")

        self.scheduler.store.update_graph_metadata(graph_id, {"human_approval_status": "approved"})
        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="system",
                correlation_id="88888888-8888-8888-8888-888888888888",
                payload={"graph_id": graph_id, "task_id": merge_task.task_id},
            ),
        )
        accepted_results = self.scheduler.run_once(count=10, block_ms=0)
        self.assertEqual(accepted_results[0]["handler_result"]["status"], "task_completed")
        self.assertEqual(self.scheduler.store.load_graph(graph_id).status, "completed")

    def test_ci_passed_cannot_complete_rerun_ci_while_fix_task_is_still_running(self) -> None:
        graph_id = "graph-ci-order"
        fix_task = self.scheduler.builder.build_task_node(
            graph_id=graph_id,
            task_id=f"{graph_id}:fix_task:1",
            task_type="fix_task",
            assigned_agent="coder",
            dependencies=(),
            status="running",
        )
        rerun_task = self.scheduler.builder.build_task_node(
            graph_id=graph_id,
            task_id=f"{graph_id}:rerun_ci:1",
            task_type="rerun_ci",
            assigned_agent="system",
            dependencies=(fix_task.task_id,),
            status="running",
        )
        graph = self.scheduler.builder.build_from_task_graph(
            AgentEvent.create(
                event_type="task_graph_created",
                source="planner",
                correlation_id="99999999-9999-9999-9999-999999999999",
                payload={
                    "graph_id": graph_id,
                    "tasks": [fix_task.to_dict(), rerun_task.to_dict()],
                    "ci_status": "running",
                    "last_fix_task_id": fix_task.task_id,
                    "last_rerun_ci_task_id": rerun_task.task_id,
                },
            )
        )
        self.scheduler.store.save_graph(graph)

        self.scheduler.bus.publish(
            CI_EVENT_STREAM,
            AgentEvent.create(
                event_type="ci_passed",
                source="ci",
                correlation_id="99999999-9999-9999-9999-999999999999",
                payload={"graph_id": graph_id},
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        self.assertEqual(results[0]["handler_result"]["status"], "ci_invalid_ordering")
        self.assertEqual(self.scheduler.store.load_task(rerun_task.task_id).status, "running")
        system_events = self._stream_events(SYSTEM_EVENT_STREAM)
        self.assertTrue(any(event.event_type == "system_alert" for event in system_events))
        self.assertTrue(any(event.event_type == "audit_log" for event in system_events))

    def test_duplicate_event_processing_is_ignored_idempotently(self) -> None:
        event = AgentEvent.create(
            event_type="issue_created",
            event_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            source="planner",
            correlation_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            payload={"graph_id": "graph-duplicate", "objective": "Implement scheduler"},
        )
        self.scheduler.bus.publish(AGENT_TASK_STREAM, event)
        self.scheduler.bus.publish(AGENT_TASK_STREAM, event)

        results = self.scheduler.run_once(count=10, block_ms=0)

        self.assertEqual(results[0]["handler_result"]["status"], "graph_created")
        self.assertEqual(results[1]["handler_result"]["status"], "duplicate_ignored")
        graph = self.scheduler.store.load_graph("graph-duplicate")
        self.assertEqual(len(graph.tasks), 6)
        self.assertEqual(self.scheduler.observability_snapshot()["processed_event_count"], 1)
        system_events = self._stream_events(SYSTEM_EVENT_STREAM)
        duplicate_audits = [
            event for event in system_events if event.event_type == "audit_log" and event.payload["category"] == "duplicate"
        ]
        self.assertEqual(len(duplicate_audits), 1)

    def _create_graph(self) -> str:
        graph_id = "graph-001"
        self.scheduler.bus.publish(
            AGENT_TASK_STREAM,
            AgentEvent.create(
                event_type="issue_created",
                source="planner",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "objective": "Implement scheduler"},
            ),
        )
        self.scheduler.run_once(count=10, block_ms=0)
        return graph_id

    def _complete_task(self, graph_id: str, task_type: str, *, source: str) -> None:
        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source=source,
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "task_id": f"{graph_id}:{task_type}"},
            ),
        )
        self.scheduler.run_once(count=10, block_ms=0)

    def _publish_ci(self, event_type: str, graph_id: str) -> None:
        self.scheduler.bus.publish(
            CI_EVENT_STREAM,
            AgentEvent.create(
                event_type=event_type,
                source="ci",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id},
            ),
        )
        self.scheduler.run_once(count=10, block_ms=0)

    def _stream_events(self, stream: str) -> list[AgentEvent]:
        return [AgentEvent.from_dict(fields) for _, fields in self.fake_redis.streams.get(stream, [])]


class MemoryRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_redis = FakeRedis()
        self.memory_runtime = MemoryRuntimeService.build_default(rules_root=Path("guardrails"))
        self.memory_runtime.bus.client = self.fake_redis
        self.memory_runtime.ensure_group()

    def test_raw_conversation_memory_payload_is_rejected(self) -> None:
        self.memory_runtime.bus.publish(
            MEMORY_EVENT_STREAM,
            AgentEvent.create(
                event_type="memory_write_requested",
                source="system",
                correlation_id="12121212-1212-1212-1212-121212121212",
                payload={
                    "graph_id": "graph-memory",
                    "task_id": "graph-memory:task",
                    "project_name": "demo",
                    "records": [],
                    "raw_conversation": [{"role": "user", "content": "secret"}],
                },
            ),
        )

        results = self.memory_runtime.run_once(count=10, block_ms=0)

        self.assertEqual(results[0]["handler_result"]["status"], "memory_payload_rejected")
        self.assertEqual(self.fake_redis.lists, {})
        system_events = [AgentEvent.from_dict(fields) for _, fields in self.fake_redis.streams[SYSTEM_EVENT_STREAM]]
        self.assertTrue(any(event.event_type == "system_alert" for event in system_events))
        self.assertTrue(any(event.event_type == "audit_log" for event in system_events))

    def test_distilled_structured_memory_payload_is_accepted_and_persisted(self) -> None:
        self.memory_runtime.bus.publish(
            MEMORY_EVENT_STREAM,
            AgentEvent.create(
                event_type="memory_write_requested",
                source="system",
                correlation_id="13131313-1313-1313-1313-131313131313",
                payload={
                    "graph_id": "graph-memory",
                    "task_id": "graph-memory:task",
                    "project_name": "demo",
                    "records": [
                        {
                            "memory_type": "decision",
                            "topic": "Scheduler audits",
                            "summary": "Use audit_log for structured traceability.",
                            "confidence": 0.9,
                            "tags": ["scheduler", "audit"],
                        }
                    ],
                },
            ),
        )

        results = self.memory_runtime.run_once(count=10, block_ms=0)

        self.assertEqual(results[0]["handler_result"]["status"], "memory_persisted")
        persisted = self.memory_runtime.manager.load_runtime_records(
            self.fake_redis,
            project_name="demo",
        )
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["topic"], "Scheduler audits")

    def test_invalid_memory_event_leaves_persistence_unchanged(self) -> None:
        valid_event = AgentEvent.create(
            event_type="memory_write_requested",
            source="system",
            correlation_id="14141414-1414-1414-1414-141414141414",
            payload={
                "graph_id": "graph-memory",
                "task_id": "graph-memory:task",
                "project_name": "demo",
                "records": [
                    {
                        "memory_type": "architecture",
                        "topic": "Runtime memory",
                        "summary": "Persist only distilled records.",
                        "confidence": 0.8,
                        "tags": ["memory"],
                    }
                ],
            },
        )
        self.memory_runtime.bus.publish(MEMORY_EVENT_STREAM, valid_event)
        self.memory_runtime.run_once(count=10, block_ms=0)

        invalid_event = AgentEvent.create(
            event_type="memory_write_requested",
            source="system",
            correlation_id="15151515-1515-1515-1515-151515151515",
            payload={
                "graph_id": "graph-memory",
                "task_id": "graph-memory:task",
                "project_name": "demo",
                "records": [
                    {
                        "memory_type": "decision",
                        "topic": "",
                        "summary": "",
                        "confidence": 1.2,
                        "tags": [""],
                    }
                ],
            },
        )
        self.memory_runtime.bus.publish(MEMORY_EVENT_STREAM, invalid_event)
        results = self.memory_runtime.run_once(count=10, block_ms=0)

        self.assertEqual(results[0]["handler_result"]["status"], "memory_payload_rejected")
        persisted = self.memory_runtime.manager.load_runtime_records(
            self.fake_redis,
            project_name="demo",
        )
        self.assertEqual(len(persisted), 1)


if __name__ == "__main__":
    unittest.main()
