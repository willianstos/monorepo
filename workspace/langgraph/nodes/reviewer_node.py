from __future__ import annotations

from workspace.langgraph.state import EngineeringGraphState


def reviewer_node(state: EngineeringGraphState) -> dict:
    return {
        "active_agent": "reviewer",
        "current_stage": "review",
        "review": {
            "status": "approved",
            "notes": ["Placeholder review approved the empty scaffold state."],
        },
        "messages": [
            {
                "role": "reviewer",
                "content": "Reviewer placeholder recorded a provisional approval.",
            }
        ],
        "artifacts": [
            {
                "kind": "review",
                "name": "review-summary",
                "content": "Placeholder review artifact for future risk assessment.",
                "producer": "reviewer",
            }
        ],
    }

