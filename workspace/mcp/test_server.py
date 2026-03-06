from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from workspace.event_bus import AGENT_RESULT_STREAM, AGENT_TASK_STREAM, MEMORY_EVENT_STREAM, AgentEvent
from workspace.mcp import FutureAgentsMCPServer, MemoryMCPAdapter, SchedulerMCPAdapter
from workspace.mcp.server import MCPRequestError
from workspace.memory import MemoryRuntimeService
from workspace.scheduler import SchedulerService
from workspace.scheduler.test_orchestration import FakeRedis


class FutureAgentsMCPServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_redis = FakeRedis()
        scheduler = SchedulerService.build_default(rules_root=Path("guardrails"), max_retry_limit=1)
        scheduler.bus.client = self.fake_redis
        scheduler.ensure_groups()

        memory_runtime = MemoryRuntimeService.build_default(rules_root=Path("guardrails"))
        memory_runtime.bus.client = self.fake_redis
        memory_runtime.ensure_group()

        self.scheduler = scheduler
        self.memory_runtime = memory_runtime
        self.server = FutureAgentsMCPServer(
            scheduler_adapter=SchedulerMCPAdapter(scheduler=scheduler),
            memory_adapter=MemoryMCPAdapter(memory_runtime=memory_runtime),
        )
        self._initialize_server()

    def test_tools_list_exposes_only_bounded_epic1_capabilities(self) -> None:
        response = self.server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

        assert response is not None
        tool_names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertIn("scheduler_get_health", tool_names)
        self.assertIn("scheduler_get_graph_state", tool_names)
        self.assertIn("scheduler_get_task_state", tool_names)
        self.assertIn("scheduler_request_issue", tool_names)
        self.assertIn("memory_submit_records", tool_names)
        self.assertNotIn("scheduler_set_task_status", tool_names)
        self.assertNotIn("scheduler_record_ci_passed", tool_names)
        self.assertNotIn("scheduler_complete_merge_task", tool_names)
        self.assertNotIn("memory_store_raw_conversation", tool_names)

    def test_scheduler_request_issue_queues_governed_issue_created_event(self) -> None:
        response = self._call_tool(
            "scheduler_request_issue",
            {"graph_id": "graph-mcp", "project_name": "demo", "objective": "Inspect MCP edge"},
        )

        payload = self._decode_tool_payload(response)
        self.assertEqual(payload["status"], "queued")
        queued_event = AgentEvent.from_dict(self.fake_redis.streams[AGENT_TASK_STREAM][-1][1])
        self.assertEqual(queued_event.event_type, "issue_created")
        self.assertEqual(queued_event.source, "system")
        self.assertEqual(queued_event.payload["requested_via"], "mcp")

        results = self.scheduler.run_once(count=10, block_ms=0)
        self.assertEqual(results[0]["handler_result"]["status"], "graph_created")
        graph = self.scheduler.store.load_graph("graph-mcp")
        self.assertIn("graph-mcp:plan_task", graph.tasks)

    def test_scheduler_transition_bypass_tool_is_rejected(self) -> None:
        response = self._dispatch_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "scheduler_set_task_status", "arguments": {"task_id": "x", "status": "completed"}},
            }
        )

        assert response is not None
        self.assertEqual(response["error"]["code"], -32602)

    def test_scheduler_ci_bypass_tool_is_rejected(self) -> None:
        response = self._dispatch_message(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "scheduler_record_ci_passed", "arguments": {"graph_id": "graph-001"}},
            }
        )

        assert response is not None
        self.assertEqual(response["error"]["code"], -32602)

    def test_scheduler_merge_bypass_tool_is_rejected(self) -> None:
        response = self._dispatch_message(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "scheduler_complete_merge_task", "arguments": {"graph_id": "graph-001"}},
            }
        )

        assert response is not None
        self.assertEqual(response["error"]["code"], -32602)

    def test_scheduler_graph_state_reports_dead_letters_and_status_counts(self) -> None:
        graph_id = "graph-dead-letter"
        self.scheduler.bus.publish(
            AGENT_TASK_STREAM,
            AgentEvent.create(
                event_type="issue_created",
                source="planner",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "objective": "Cause a retry"},
            ),
        )
        self.scheduler.run_once(count=10, block_ms=0)
        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_failed",
                source="planner",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "task_id": f"{graph_id}:plan_task", "reason": "fail once"},
            ),
        )
        self.scheduler.run_once(count=10, block_ms=0)
        self.scheduler.bus.publish(
            AGENT_RESULT_STREAM,
            AgentEvent.create(
                event_type="task_failed",
                source="planner",
                correlation_id="11111111-1111-1111-1111-111111111111",
                payload={"graph_id": graph_id, "task_id": f"{graph_id}:plan_task", "reason": "fail twice"},
            ),
        )
        self.scheduler.run_once(count=10, block_ms=0)

        response = self._call_tool("scheduler_get_graph_state", {"graph_id": graph_id})
        payload = self._decode_tool_payload(response)

        self.assertEqual(payload["graph_id"], graph_id)
        self.assertIn("task_counts", payload)
        self.assertEqual(len(payload["dead_letters"]), 1)

    def test_memory_submit_records_rejects_raw_conversation_payloads(self) -> None:
        response = self._call_tool(
            "memory_submit_records",
            {
                "project_name": "demo",
                "graph_id": "graph-memory",
                "task_id": "graph-memory:task",
                "records": [],
                "raw_conversation": [{"role": "user", "content": "secret"}],
            },
        )

        payload = self._decode_tool_payload(response)
        self.assertEqual(payload["status"], "rejected")
        self.assertFalse(payload["published"])
        self.assertEqual(self.fake_redis.streams[MEMORY_EVENT_STREAM], [])

    def test_memory_submit_records_queues_structured_payloads_for_existing_runtime_path(self) -> None:
        response = self._call_tool(
            "memory_submit_records",
            {
                "project_name": "demo",
                "graph_id": "graph-memory",
                "task_id": "graph-memory:task",
                "records": [
                    {
                        "memory_type": "decision",
                        "topic": "Epic 1",
                        "summary": "Use the memory runtime path only.",
                        "confidence": 0.9,
                        "tags": ["mcp", "memory"],
                    }
                ],
            },
        )

        payload = self._decode_tool_payload(response)
        self.assertEqual(payload["status"], "queued")
        self.assertTrue(payload["published"])

        results = self.memory_runtime.run_once(count=10, block_ms=0)
        self.assertEqual(results[0]["handler_result"]["status"], "memory_persisted")
        persisted = self.memory_runtime.manager.load_runtime_records(self.fake_redis, project_name="demo")
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["topic"], "Epic 1")

    def _initialize_server(self) -> None:
        response = self.server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert response is not None
        self.assertEqual(response["result"]["serverInfo"]["name"], "future-agents-mcp")
        self.server.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, Any]:
        response = self._dispatch_message(
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        assert response is not None
        return response

    def _dispatch_message(self, message: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.server.handle_message(message)
        except MCPRequestError as exc:
            return {"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": exc.code, "message": exc.message}}
        assert response is not None
        return response

    @staticmethod
    def _decode_tool_payload(response: dict[str, Any]) -> dict[str, Any]:
        content = response["result"]["content"][0]["text"]
        return json.loads(content)


if __name__ == "__main__":
    unittest.main()
