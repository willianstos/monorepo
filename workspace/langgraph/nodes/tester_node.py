from __future__ import annotations

from workspace.langgraph.state import EngineeringGraphState


def tester_node(state: EngineeringGraphState) -> dict:
    return {
        "active_agent": "tester",
        "current_stage": "testing",
        "test_results": {
            "status": "placeholder",
            "summary": "No real tests executed yet.",
            "passed": True,
        },
        "messages": [
            {
                "role": "tester",
                "content": "Tester placeholder prepared the validation checkpoint.",
            }
        ],
        "artifacts": [
            {
                "kind": "test-report",
                "name": "validation-report",
                "content": "Placeholder test report for future automated checks.",
                "producer": "tester",
            }
        ],
    }

