from __future__ import annotations

from operator import add
from pathlib import Path
from typing import Annotated, Any, Literal, NotRequired, TypedDict

from workspace.event_bus.events import StreamName
from workspace.memory.schemas import MemoryRecord, RetrievedMemory
from workspace.providers.model_auditor import ModelAuditResult
from workspace.providers.model_router import ModelRouteDecision

AgentName = Literal["planner", "coder", "tester", "reviewer"]
ProviderName = Literal["local", "codex", "claude"]
StageName = Literal[
    "intake",
    "planning",
    "implementation",
    "testing",
    "review",
    "approval",
    "merge",
    "completed",
    "blocked",
]


class TaskMessage(TypedDict):
    role: str
    content: str


class TaskArtifact(TypedDict):
    kind: str
    name: str
    content: str
    producer: AgentName


class ReviewRecord(TypedDict, total=False):
    status: Literal["pending", "approved", "changes_requested", "blocked"]
    notes: list[str]


class EngineeringGraphState(TypedDict, total=False):
    task_id: str
    objective: str
    project_name: str
    project_path: str
    project_context_path: str
    event_bus_enabled: bool
    event_bus_streams: list[StreamName]
    task_graph_id: str
    task_graph: dict[str, Any]
    ci_status: str
    scheduler_consumer_group: str
    subscribed_streams: list[StreamName]
    pending_events: list[dict[str, Any]]
    published_events: list[dict[str, Any]]
    consumer_groups: dict[str, str]
    available_skills_index: dict[str, list[str]]
    selected_skill: str | None
    skill_context: dict[str, Any] | None
    working_memory: dict[str, Any]
    session_memory: list[MemoryRecord]
    long_term_memory_hits: list[RetrievedMemory]
    memory_flush_required: bool
    memory_flush_candidates: list[MemoryRecord]
    memory_retrieval_order: list[str]
    architecture_docs: list[str]
    module_docs: list[str]
    prompt_docs: list[str]
    task_type: str
    model_audit: ModelAuditResult | None
    model_route: ModelRouteDecision | None
    gateway_base_url: str
    gateway_chat_endpoint: str
    provider_name: ProviderName
    model_profile: str
    model_name: str
    active_agent: AgentName
    current_stage: StageName
    next_stage: NotRequired[StageName]
    runtime_context: dict[str, Any]
    task_context: dict[str, Any]
    plan: dict[str, Any]
    implementation_notes: list[str]
    changed_files: list[str]
    test_results: dict[str, Any]
    review: ReviewRecord
    approvals: dict[str, bool]
    risks: list[str]
    errors: list[str]
    iteration: int
    max_iterations: int
    messages: Annotated[list[TaskMessage], add]
    artifacts: Annotated[list[TaskArtifact], add]


def make_initial_state(
    objective: str,
    project_name: str,
    project_path: str,
    project_context_path: str | None = None,
    provider_name: ProviderName | None = None,
    model_profile: str | None = None,
) -> EngineeringGraphState:
    context_path = Path(project_context_path or ".context")

    return {
        "task_id": "placeholder-task",
        "objective": objective,
        "project_name": project_name,
        "project_path": project_path,
        "project_context_path": str(context_path),
        "event_bus_enabled": True,
        "event_bus_streams": [
            "agent_tasks",
            "agent_results",
            "ci_events",
            "memory_events",
            "system_events",
        ],
        "task_graph_id": "placeholder-task",
        "task_graph": {"graph_id": "placeholder-task", "nodes": []},
        "ci_status": "unknown",
        "scheduler_consumer_group": "scheduler-group",
        "subscribed_streams": ["agent_tasks", "agent_results", "ci_events", "system_events"],
        "pending_events": [],
        "published_events": [],
        "consumer_groups": {
            "planner": "planner-group",
            "coder": "coder-group",
            "tester": "tester-group",
            "reviewer": "reviewer-group",
            "scheduler": "scheduler-group",
        },
        "available_skills_index": {},
        "selected_skill": None,
        "skill_context": None,
        "working_memory": {
            "current_tasks": [],
            "agent_state": {},
            "partial_outputs": [],
        },
        "session_memory": [],
        "long_term_memory_hits": [],
        "memory_flush_required": True,
        "memory_flush_candidates": [],
        "memory_retrieval_order": [
            "structured_memory",
            "recent_sessions",
        ],
        "architecture_docs": [
            str(context_path / "docs" / "architecture.md"),
            str(context_path / "docs" / "data-flow.md"),
            str(context_path / "docs" / "security.md"),
        ],
        "module_docs": [
            str(context_path / "docs" / "project-overview.md"),
            str(context_path / "docs" / "development-workflow.md"),
            str(context_path / "docs" / "tooling.md"),
            str(context_path / "docs" / "testing-strategy.md"),
        ],
        "prompt_docs": [
            str(context_path / "docs" / "README.md"),
            str(context_path / "docs" / "glossary.md"),
            str(context_path / "docs" / "development-workflow.md"),
        ],
        "task_type": "routing",
        "model_audit": None,
        "model_route": None,
        "gateway_base_url": "http://localhost:4000",
        "gateway_chat_endpoint": "http://localhost:4000/v1/chat/completions",
        "provider_name": provider_name or "claude",
        "model_profile": model_profile or "strategic_reasoning",
        "model_name": "claude-code",
        "runtime_context": {},
        "task_context": {},
        "active_agent": "planner",
        "current_stage": "intake",
        "iteration": 0,
        "max_iterations": 3,
        "implementation_notes": [],
        "changed_files": [],
        "approvals": {},
        "risks": [],
        "errors": [],
        "messages": [],
        "artifacts": [],
    }
