from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, TypedDict

TaskType = Literal[
    "classify_request",
    "route_small_task",
    "summarize_context",
    "distill_memory",
    "normalize_json",
    "extract_structured_fields",
    "issue_triage",
    "choose_skill_category",
    "explain_policy",
    "summarize_logs",
    "file_inventory_summary",
    "planning",
    "deep_debugging",
    "complex_architecture_decision",
    "implementation",
    "review_analysis",
    "research_analysis",
    "multi_step_reasoning",
]


class ModelAuditResult(TypedDict):
    task_type: str
    recommended_model: str
    reason: str
    confidence: float


LOCAL_TASK_TYPES: set[TaskType] = {
    "classify_request",
    "route_small_task",
    "summarize_context",
    "distill_memory",
    "normalize_json",
    "extract_structured_fields",
    "issue_triage",
    "choose_skill_category",
    "explain_policy",
    "summarize_logs",
    "file_inventory_summary",
}

TASK_KEYWORDS: dict[TaskType, tuple[str, ...]] = {
    "classify_request": ("classify", "classification", "label", "categorize"),
    "route_small_task": ("route", "routing", "handoff", "dispatch"),
    "summarize_context": ("summarize context", "compress context", "context summary", "summarize notes"),
    "distill_memory": ("distill memory", "memory summary", "memory distillation", "flush memory"),
    "normalize_json": ("normalize json", "json normalization", "structured json", "schema object"),
    "extract_structured_fields": ("extract", "pull facts", "structured fields", "extract information"),
    "issue_triage": ("triage", "severity", "bug class", "issue triage"),
    "choose_skill_category": ("skill category", "choose skill", "skill selection", "pick skill"),
    "explain_policy": ("explain policy", "policy summary", "guardrail summary", "command policy"),
    "summarize_logs": ("summarize logs", "log summary", "trace summary", "error log"),
    "file_inventory_summary": ("file inventory", "inventory summary", "directory summary", "list files"),
    "planning": ("plan", "planning", "roadmap", "sequence tasks"),
    "deep_debugging": ("debug", "root cause", "hard bug", "complex issue"),
    "complex_architecture_decision": ("architecture", "system design", "design blueprint", "tradeoff"),
    "implementation": ("implement", "write code", "repo edit", "refactor", "patch"),
    "review_analysis": ("review", "code review", "risk review", "review findings"),
    "research_analysis": ("research", "compare options", "investigate", "survey"),
    "multi_step_reasoning": ("multi-step", "plan and execute", "chain of thought", "workflow"),
}


@dataclass(frozen=True)
class ModelInfrastructureAuditor:
    local_model: str = "local:qwen3.5:9b"
    codex_model: str = "codex-cli"
    claude_model: str = "claude-code"
    escalation_threshold: float = 0.6

    def audit(self, task_description: str) -> ModelAuditResult:
        task_type, confidence = self.classify_task(task_description)
        recommended_model, reason = self.recommend_model(task_type, confidence)
        return {
            "task_type": task_type,
            "recommended_model": recommended_model,
            "reason": reason,
            "confidence": confidence,
        }

    def classify_task(self, task_description: str) -> tuple[TaskType, float]:
        lowered = task_description.lower()
        matches: list[tuple[TaskType, int]] = []

        for task_type, keywords in TASK_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in lowered)
            if score:
                matches.append((task_type, score))

        if not matches:
            return "multi_step_reasoning", 0.45

        task_type, score = max(matches, key=lambda item: item[1])
        confidence = min(0.99, 0.58 + score * 0.12)
        return task_type, confidence

    def recommend_model(self, task_type: TaskType, confidence: float) -> tuple[str, str]:
        if task_type in LOCAL_TASK_TYPES and confidence >= self.escalation_threshold:
            return (
                self.local_model,
                "Task is cheap, bounded, and low-risk. Keep it on the local Ollama helper model.",
            )

        if task_type == "implementation":
            return (
                self.codex_model,
                "Task requires repository edits or implementation authority, which fits Codex best.",
            )

        if task_type in {
            "planning",
            "deep_debugging",
            "complex_architecture_decision",
            "review_analysis",
            "research_analysis",
            "multi_step_reasoning",
        }:
            return (
                self.claude_model,
                "Task requires planning, architecture, debugging, review, or higher-order reasoning suited to Claude.",
            )

        return (
            self.claude_model,
            "Task is ambiguous or sensitive enough to escalate to Claude instead of the local helper model.",
        )

    def audit_many(self, tasks: Iterable[str]) -> list[ModelAuditResult]:
        return [self.audit(task) for task in tasks]
