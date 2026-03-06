from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, TypedDict

TaskType = Literal[
    "classification",
    "routing",
    "tool_formatting",
    "json_generation",
    "extracting_information",
    "summarizing_logs",
    "parsing_code",
    "rag_retrieval",
    "small_edits",
    "small_code_generation",
    "planning",
    "deep_reasoning",
    "complex_architecture_design",
    "large_code_generation",
    "difficult_debugging",
    "research_tasks",
    "multi_step_reasoning",
]


class ModelAuditResult(TypedDict):
    task_type: str
    recommended_model: str
    reason: str
    confidence: float


LOCAL_TASK_TYPES: set[TaskType] = {
    "classification",
    "routing",
    "tool_formatting",
    "json_generation",
    "extracting_information",
    "summarizing_logs",
    "parsing_code",
    "rag_retrieval",
    "small_edits",
    "small_code_generation",
}

CLOUD_TASK_TYPES: set[TaskType] = {
    "deep_reasoning",
    "complex_architecture_design",
    "large_code_generation",
    "difficult_debugging",
    "research_tasks",
    "multi_step_reasoning",
}

TASK_KEYWORDS: dict[TaskType, tuple[str, ...]] = {
    "classification": ("classify", "classification", "label", "categorize"),
    "routing": ("route", "routing", "handoff", "dispatch"),
    "tool_formatting": ("format tool", "tool payload", "tool formatting", "json schema"),
    "json_generation": ("json", "structured output", "schema object", "json generation"),
    "extracting_information": ("extract", "pull facts", "parse output", "extract information"),
    "summarizing_logs": ("summarize logs", "log summary", "trace summary", "error log"),
    "parsing_code": ("parse code", "inspect file", "read code", "understand code"),
    "rag_retrieval": ("rag", "retrieve context", "semantic search", "vector retrieval"),
    "small_edits": ("small edit", "minor fix", "one-line fix", "tiny change"),
    "small_code_generation": ("small code", "simple script", "small generation", "snippet"),
    "planning": ("plan", "planning", "roadmap", "sequence tasks"),
    "deep_reasoning": ("deep reasoning", "hard problem", "complex reasoning"),
    "complex_architecture_design": ("architecture", "system design", "design blueprint", "tradeoff"),
    "large_code_generation": ("large code", "generate module", "repo edit", "refactor", "implementation"),
    "difficult_debugging": ("debug", "root cause", "hard bug", "complex issue"),
    "research_tasks": ("research", "compare options", "investigate", "survey"),
    "multi_step_reasoning": ("multi-step", "plan and execute", "chain of thought", "workflow"),
}


@dataclass(frozen=True)
class ModelInfrastructureAuditor:
    local_model: str = "local:qwen3.5-9b"
    codex_model: str = "codex-cli"
    claude_model: str = "claude-code"
    gemini_model: str = "gemini"
    openai_model: str = "openai"
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
                "Task is operational or lightweight. Prefer the local Ollama Qwen3.5 9B route to minimize cloud cost.",
            )

        if task_type in {"large_code_generation"}:
            return (
                self.codex_model,
                "Task requires large-scale code generation or repository edits, which fits Codex best.",
            )

        if task_type in {"planning", "complex_architecture_design", "deep_reasoning", "difficult_debugging"}:
            return (
                self.claude_model,
                "Task requires deep reasoning, planning, or difficult debugging suited to Claude.",
            )

        if task_type in {"research_tasks"}:
            return (
                self.gemini_model,
                "Task requires research or large-context analysis, which is routed to Gemini.",
            )

        if task_type in {"multi_step_reasoning"}:
            return (
                self.openai_model if confidence < self.escalation_threshold else self.claude_model,
                "Task spans multiple steps; escalate to a stronger cloud reasoning model when local confidence is low.",
            )

        return (
            self.openai_model,
            "Task does not cleanly fit a specialized lane, so use OpenAI as the general cloud fallback.",
        )

    def audit_many(self, tasks: Iterable[str]) -> list[ModelAuditResult]:
        return [self.audit(task) for task in tasks]
