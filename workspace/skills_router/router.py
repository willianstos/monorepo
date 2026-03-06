from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_SKILL_FILE = "SKILL.md"

KEYWORD_TO_CATEGORY = {
    "security": (
        "security",
        "audit",
        "auth",
        "vulnerability",
        "permission",
        "compliance",
    ),
    "testing": ("test", "qa", "coverage", "regression", "assert", "verification"),
    "performance": ("performance", "optimize", "latency", "throughput", "profiling"),
    "refactor": ("refactor", "cleanup", "tech debt", "simplify", "restructure"),
    "frontend": ("frontend", "ui", "ux", "component", "react", "next", "css"),
    "backend": ("backend", "api", "service", "server", "endpoint", "worker"),
    "database": ("database", "sql", "postgres", "mysql", "schema", "migration"),
}


@dataclass(frozen=True)
class SkillSelection:
    category: str
    skill_name: str
    skill_dir: str
    skill_file: str
    content: str


class SkillRouter:
    """Load one indexed skill at a time and only read its SKILL.md."""

    def __init__(
        self,
        index_path: Path | None = None,
        skill_roots: tuple[Path, ...] | None = None,
    ) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self.index_path = index_path or repo_root / "workspace" / "skills_router" / "skills_index.json"
        self.skill_roots = skill_roots or (
            repo_root / ".agent" / "skills",
            repo_root / ".context" / "skills",
            repo_root / ".agent" / "catalogs" / "antigravity-awesome-skills" / "skills",
        )

    def load_index(self) -> dict[str, list[str]]:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def determine_category(self, objective: str, fallback: str = "backend") -> str:
        lowered = objective.lower()
        for category, keywords in KEYWORD_TO_CATEGORY.items():
            if any(keyword in lowered for keyword in keywords):
                return category
        return fallback

    def select_skill(self, category: str, index: dict[str, list[str]] | None = None) -> str | None:
        skill_index = index or self.load_index()
        skills = skill_index.get(category, [])
        return skills[0] if skills else None

    def load_skill(self, skill_name: str, category: str | None = None) -> SkillSelection:
        skill_dir = self.resolve_skill_dir(skill_name)
        skill_file = skill_dir / ALLOWED_SKILL_FILE
        content = skill_file.read_text(encoding="utf-8")
        return SkillSelection(
            category=category or "unknown",
            skill_name=skill_name,
            skill_dir=str(skill_dir),
            skill_file=str(skill_file),
            content=content,
        )

    def discard_skill_context(self) -> dict[str, Any]:
        return {
            "skill_name": None,
            "skill_file": None,
            "content": None,
            "discarded": True,
        }

    def resolve_skill_dir(self, skill_name: str) -> Path:
        for root in self.skill_roots:
            candidate = root / skill_name
            if candidate.is_dir():
                skill_file = candidate / ALLOWED_SKILL_FILE
                if skill_file.is_file():
                    return candidate
        raise FileNotFoundError(
            f"Indexed skill '{skill_name}' was not found in configured roots. "
            "Skill routing does not scan the full skills tree."
        )
