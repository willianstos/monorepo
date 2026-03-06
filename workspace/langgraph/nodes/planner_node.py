from __future__ import annotations

from workspace.langgraph.state import EngineeringGraphState
from workspace.providers.model_router import ModelRouter
from workspace.skills_router.router import SkillRouter


def planner_node(state: EngineeringGraphState) -> dict:
    router = SkillRouter()
    model_router = ModelRouter()
    skill_category = router.determine_category(state.get("objective", ""))
    route = model_router.route_task(state.get("objective", ""))
    audit = model_router.auditor.audit(state.get("objective", ""))

    return {
        "active_agent": "planner",
        "current_stage": "planning",
        "task_type": audit["task_type"],
        "model_audit": audit,
        "model_route": {
            "task_type": route.task_type,
            "provider": route.provider,
            "model": route.model,
            "backend_type": route.backend_type,
            "transport": route.transport,
            "target": route.target,
            "reason": route.reason,
            "confidence": route.confidence,
        },
        "provider_name": route.provider,
        "model_name": route.model,
        "task_context": {
            **state.get("task_context", {}),
            "skill_category": skill_category,
        },
        "plan": {
            "status": "placeholder",
            "acceptance_criteria": ["Define scope", "Design solution", "Implement", "Validate"],
            "skill_category": skill_category,
            "model_route": {
                "provider": route.provider,
                "model": route.model,
                "backend_type": route.backend_type,
                "transport": route.transport,
                "target": route.target,
            },
        },
        "messages": [
            {
                "role": "planner",
                "content": (
                    "Planner placeholder created an initial execution scaffold and "
                    f"determined the skill category '{skill_category}' with gateway route "
                    f"'{route.provider}:{route.model}'."
                ),
            }
        ],
        "artifacts": [
            {
                "kind": "plan",
                "name": "execution-plan",
                "content": "Placeholder plan for future decomposition logic.",
                "producer": "planner",
            },
            {
                "kind": "model-audit",
                "name": "model-routing-decision",
                "content": str(
                    {
                        "audit": audit,
                        "route": {
                            "provider": route.provider,
                            "model": route.model,
                            "backend_type": route.backend_type,
                            "transport": route.transport,
                            "target": route.target,
                        },
                    }
                ),
                "producer": "planner",
            }
        ],
    }
