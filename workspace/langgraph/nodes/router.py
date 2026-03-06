from __future__ import annotations

from langgraph.graph import END

from workspace.langgraph.state import EngineeringGraphState


def route_after_planner(state: EngineeringGraphState) -> str:
    return "skill_router"


def route_after_skill_router(state: EngineeringGraphState) -> str:
    return "coder"


def route_after_coder(state: EngineeringGraphState) -> str:
    return "tester"


def route_after_tester(state: EngineeringGraphState) -> str:
    test_results = state.get("test_results", {})
    if test_results.get("passed", True):
        return "reviewer"
    return "coder"


def route_after_reviewer(state: EngineeringGraphState) -> str:
    review_status = state.get("review", {}).get("status", "pending")
    if review_status in {"changes_requested", "blocked"}:
        return "coder"
    return END
