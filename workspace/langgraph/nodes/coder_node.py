from __future__ import annotations

from workspace.langgraph.state import EngineeringGraphState
from workspace.skills_router.router import SkillRouter


def coder_node(state: EngineeringGraphState) -> dict:
    router = SkillRouter()
    skill_name = state.get("selected_skill")
    skill_category = state.get("task_context", {}).get("skill_category", "backend")
    skill_context = None

    if skill_name:
        selection = router.load_skill(skill_name, category=skill_category)
        skill_context = {
            "category": selection.category,
            "skill_name": selection.skill_name,
            "skill_dir": selection.skill_dir,
            "skill_file": selection.skill_file,
            "content": selection.content,
            "load_policy": "single-file-only",
        }

    return {
        "active_agent": "coder",
        "current_stage": "implementation",
        "changed_files": state.get("changed_files", []),
        "skill_context": skill_context,
        "messages": [
            {
                "role": "coder",
                "content": (
                    "Coder placeholder is ready to apply scoped code changes "
                    f"with indexed skill '{skill_name or 'none'}'."
                ),
            }
        ],
        "artifacts": [
            {
                "kind": "code-change",
                "name": "pending-change-set",
                "content": "Placeholder for generated patches and file edits.",
                "producer": "coder",
            }
        ],
    }
