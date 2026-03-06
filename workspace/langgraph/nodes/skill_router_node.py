from __future__ import annotations

from workspace.langgraph.state import EngineeringGraphState
from workspace.skills_router.router import SkillRouter


def skill_router_node(state: EngineeringGraphState) -> dict:
    router = SkillRouter()
    skill_index = router.load_index()
    skill_category = state.get("task_context", {}).get("skill_category", "backend")
    selected_skill = router.select_skill(skill_category, skill_index)

    return {
        "current_stage": "planning",
        "available_skills_index": skill_index,
        "selected_skill": selected_skill,
        "messages": [
            {
                "role": "skill_router",
                "content": (
                    f"Skill router selected category '{skill_category}' and skill "
                    f"'{selected_skill or 'none'}' using the indexed registry."
                ),
            }
        ],
        "artifacts": [
            {
                "kind": "skill-selection",
                "name": "selected-skill",
                "content": selected_skill or "No indexed skill available for the detected category.",
                "producer": "planner",
            }
        ],
    }

