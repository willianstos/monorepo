from __future__ import annotations

import os
import unittest
from pathlib import Path

from workspace.event_bus import AGENT_RESULT_STREAM, AGENT_TASK_STREAM, CI_EVENT_STREAM, AgentEvent, RedisStreamBus
from workspace.scheduler import CIEventHandler, DagBuilder, GuardrailEnforcer, RedisDagStore, SchedulerService, TaskDispatcher


class RedisIntegrationTests(unittest.TestCase):
    host = os.getenv("REDIS_INTEGRATION_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_INTEGRATION_PORT", "6380"))
    db = int(os.getenv("REDIS_INTEGRATION_DB", "15"))

    @classmethod
    def setUpClass(cls) -> None:
        try:
            bus = RedisStreamBus(host=cls.host, port=cls.port, db=cls.db)
            if not bus.ping():
                raise RuntimeError("Redis ping returned false.")
            bus.require_client().flushdb()
        except Exception as exc:  # noqa: BLE001
            raise unittest.SkipTest(f"Redis integration tests require a running Redis instance: {exc}") from exc

    def setUp(self) -> None:
        self.bus = RedisStreamBus(host=self.host, port=self.port, db=self.db)
        self.bus.require_client().flushdb()
        self.store = RedisDagStore(bus=self.bus)
        self.builder = DagBuilder()
        self.guardrails = GuardrailEnforcer(rules_root=Path("guardrails"))
        self.dispatcher = TaskDispatcher(bus=self.bus, store=self.store, guardrails=self.guardrails)
        self.scheduler = SchedulerService(
            bus=self.bus,
            store=self.store,
            builder=self.builder,
            dispatcher=self.dispatcher,
            ci_handler=CIEventHandler(builder=self.builder),
            guardrails=self.guardrails,
            max_retry_limit=1,
        )
        self.scheduler.ensure_groups()

    def test_consumer_group_reads_ack_and_replay_pending_entries(self) -> None:
        group_name = "integration-group"
        consumer_name = "consumer-a"
        self.bus.ensure_consumer_group(AGENT_TASK_STREAM, group_name, start_id="0")
        self.bus.publish(
            AGENT_TASK_STREAM,
            AgentEvent.create(
                event_type="issue_created",
                source="planner",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": "graph-replay", "objective": "Replay scheduler event"},
            ),
        )

        first_read = self.bus.read_group(
            group_name,
            consumer_name,
            {AGENT_TASK_STREAM: ">"},
            count=1,
            block_ms=0,
        )
        self.assertEqual(len(first_read), 1)

        replay_read = self.bus.read_group(
            group_name,
            consumer_name,
            {AGENT_TASK_STREAM: "0"},
            count=1,
            block_ms=0,
        )
        self.assertEqual(len(replay_read), 1)
        self.assertEqual(replay_read[0].event.event_id, first_read[0].event.event_id)

        self.bus.acknowledge(AGENT_TASK_STREAM, group_name, first_read[0].event_id)
        pending_after_ack = self.bus.read_group(
            group_name,
            consumer_name,
            {AGENT_TASK_STREAM: "0"},
            count=1,
            block_ms=0,
        )
        self.assertEqual(pending_after_ack, [])

    def test_duplicate_event_is_ignored_idempotently(self) -> None:
        event = AgentEvent.create(
            event_type="issue_created",
            event_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            source="planner",
            correlation_id="22222222-2222-2222-2222-222222222222",
            payload={"graph_id": "graph-duplicate", "objective": "Build duplicate-safe graph"},
        )
        self.bus.publish(AGENT_TASK_STREAM, event)
        self.bus.publish(AGENT_TASK_STREAM, event)

        results = self.scheduler.run_once(count=10, block_ms=0)

        self.assertEqual(results[0]["handler_result"]["status"], "graph_created")
        self.assertEqual(results[1]["handler_result"]["status"], "duplicate_ignored")
        graph = self.store.load_graph("graph-duplicate")
        self.assertEqual(len(graph.tasks), 6)
        self.assertEqual(self.scheduler.observability_snapshot()["processed_event_count"], 1)

    def test_invalid_ci_ordering_emits_audit_and_preserves_rerun_state(self) -> None:
        fix_task = self.builder.build_task_node(
            graph_id="graph-ci",
            task_id="graph-ci:fix_task:1",
            task_type="fix_task",
            assigned_agent="coder",
            dependencies=(),
            status="running",
        )
        rerun_task = self.builder.build_task_node(
            graph_id="graph-ci",
            task_id="graph-ci:rerun_ci:1",
            task_type="rerun_ci",
            assigned_agent="system",
            dependencies=(fix_task.task_id,),
            status="running",
        )
        graph = self.builder.build_from_task_graph(
            AgentEvent.create(
                event_type="task_graph_created",
                source="planner",
                correlation_id="33333333-3333-3333-3333-333333333333",
                payload={
                    "graph_id": "graph-ci",
                    "tasks": [fix_task.to_dict(), rerun_task.to_dict()],
                    "ci_status": "running",
                    "last_fix_task_id": fix_task.task_id,
                    "last_rerun_ci_task_id": rerun_task.task_id,
                },
            )
        )
        self.store.save_graph(graph)

        self.bus.publish(
            CI_EVENT_STREAM,
            AgentEvent.create(
                event_type="ci_passed",
                source="ci",
                correlation_id="33333333-3333-3333-3333-333333333333",
                payload={"graph_id": "graph-ci"},
            ),
        )

        results = self.scheduler.run_once(count=10, block_ms=0)

        self.assertEqual(results[0]["handler_result"]["status"], "ci_invalid_ordering")
        self.assertEqual(self.store.load_task(rerun_task.task_id).status, "running")
        system_events = self.bus.read_streams({"system_events": "0"}, count=20, block_ms=0)
        event_types = [record.event.event_type for record in system_events]
        self.assertIn("system_alert", event_types)
        self.assertIn("audit_log", event_types)

    def test_dead_letter_path_preserves_graph_and_task_consistency(self) -> None:
        self.bus.publish(
            AGENT_TASK_STREAM,
            AgentEvent.create(
                event_type="issue_created",
                source="planner",
                correlation_id="44444444-4444-4444-4444-444444444444",
                payload={"graph_id": "graph-dead-letter", "objective": "Exercise dead-letter path"},
            ),
        )
        self.scheduler.run_once(count=10, block_ms=0)

        self.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_completed",
                source="planner",
                correlation_id="44444444-4444-4444-4444-444444444444",
                payload={"graph_id": "graph-dead-letter", "task_id": "graph-dead-letter:plan_task"},
            ),
        )
        self.scheduler.run_once(count=10, block_ms=0)

        first_failure_event = AgentEvent.create(
            event_type="task_failed",
            source="coder",
            correlation_id="44444444-4444-4444-4444-444444444444",
            payload={
                "graph_id": "graph-dead-letter",
                "task_id": "graph-dead-letter:implement_task",
                "reason": "compile failed",
            },
        )
        second_failure_event = AgentEvent.create(
            event_type="task_failed",
            source="coder",
            correlation_id="44444444-4444-4444-4444-444444444444",
            payload={
                "graph_id": "graph-dead-letter",
                "task_id": "graph-dead-letter:implement_task",
                "reason": "compile failed",
            },
        )
        self.bus.publish(AGENT_RESULT_STREAM, first_failure_event)
        self.scheduler.run_once(count=10, block_ms=0)
        self.bus.publish(AGENT_RESULT_STREAM, second_failure_event)
        results = self.scheduler.run_once(count=10, block_ms=0)

        dead_lettered = [item for item in results if item["handler_result"]["status"] == "task_dead_lettered"]
        self.assertEqual(len(dead_lettered), 1)
        graph = self.store.load_graph("graph-dead-letter")
        self.assertEqual(graph.status, "requires_human_attention")
        self.assertEqual(
            self.store.load_task("graph-dead-letter:implement_task").status,
            "failed",
        )
        dead_letters = self.bus.require_client().lrange(self.store.dead_letter_key("graph-dead-letter"), 0, -1)
        self.assertEqual(len(dead_letters), 1)


if __name__ == "__main__":
    unittest.main()
