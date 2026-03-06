from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GraphNode = Literal["planner", "skill_router", "coder", "tester", "reviewer"]
NodeKind = Literal["agent", "router"]


@dataclass(frozen=True)
class NodeBlueprint:
    name: GraphNode
    kind: NodeKind
    agent_module: str | None
    node_module: str
    purpose: str


@dataclass(frozen=True)
class LangGraphBlueprint:
    name: str
    orchestration_backend: str
    entrypoint: GraphNode
    default_route: tuple[GraphNode, ...]
    nodes: tuple[NodeBlueprint, ...]
    return_routes: dict[GraphNode, tuple[GraphNode, ...]]
    context_sources: tuple[str, ...]
    skill_router_module: str
    skill_loading_policy: str
    model_auditor_module: str
    model_router_module: str
    model_routing_policy: str
    gateway_server_module: str
    gateway_router_module: str
    gateway_endpoint: str
    event_bus_module: str
    consumer_module: str
    event_streams: tuple[str, ...]
    communication_policy: str
    scheduler_module: str
    scheduler_policy: str
    memory_manager_module: str
    memory_flush_policy: str
    runtime_dependencies: tuple[str, ...]


LANGGRAPH_BLUEPRINT = LangGraphBlueprint(
    name="local-first-coding-assistant-blueprint",
    orchestration_backend="langgraph",
    entrypoint="planner",
    default_route=("planner", "skill_router", "coder", "tester", "reviewer"),
    nodes=(
        NodeBlueprint(
            name="planner",
            kind="agent",
            agent_module="workspace.agents.planner.agent",
            node_module="workspace.langgraph.nodes.planner_node",
            purpose="Interpret issues, prepare planning inputs, and publish work requests into Redis Streams.",
        ),
        NodeBlueprint(
            name="skill_router",
            kind="router",
            agent_module=None,
            node_module="workspace.langgraph.nodes.skill_router_node",
            purpose="Select one indexed skill without scanning or loading the full skills tree.",
        ),
        NodeBlueprint(
            name="coder",
            kind="agent",
            agent_module="workspace.agents.coder.agent",
            node_module="workspace.langgraph.nodes.coder_node",
            purpose="Write implementation code only and publish results back to the event bus.",
        ),
        NodeBlueprint(
            name="tester",
            kind="agent",
            agent_module="workspace.agents.tester.agent",
            node_module="workspace.langgraph.nodes.tester_node",
            purpose="Own tests and fixtures only, then publish test results to Redis Streams.",
        ),
        NodeBlueprint(
            name="reviewer",
            kind="agent",
            agent_module="workspace.agents.reviewer.agent",
            node_module="workspace.langgraph.nodes.reviewer_node",
            purpose="Validate code quality, guardrails, and consistency before human approval and merge.",
        ),
    ),
    return_routes={
        "skill_router": ("coder",),
        "tester": ("coder",),
        "reviewer": ("coder",),
    },
    context_sources=(
        ".context/docs/architecture.md",
        ".context/docs/project-overview.md",
        ".context/docs/README.md",
    ),
    skill_router_module="workspace.skills_router.router",
    skill_loading_policy="indexed-single-skill-skill-md-only-discard-after-step",
    model_auditor_module="workspace.providers.model_auditor",
    model_router_module="workspace.providers.model_router",
    model_routing_policy="local-first-helper-only-escalate-authority-to-codex-or-claude",
    gateway_server_module="workspace.gateway.server",
    gateway_router_module="workspace.gateway.router",
    gateway_endpoint="http://localhost:4000/v1/chat/completions",
    event_bus_module="workspace.event_bus.bus",
    consumer_module="workspace.event_bus.consumers",
    event_streams=("agent_tasks", "agent_results", "ci_events", "memory_events", "system_events"),
    communication_policy="agents-publish-and-consume-via-redis-streams-no-direct-agent-calls",
    scheduler_module="workspace.scheduler.service",
    scheduler_policy="separate-stateless-scheduler-service-persists-dag-state-in-redis-and-reacts-to-ci-events",
    memory_manager_module="workspace.memory.manager",
    memory_flush_policy="flush-before-context-discard-distilled-records-only",
    runtime_dependencies=(
        "workspace.runtime.runner",
        "workspace.runtime.assistant_runtime",
        "workspace.runtime.task_executor",
        "workspace.providers.model_auditor",
        "workspace.providers.model_router",
        "workspace.gateway.server",
        "workspace.gateway.router",
        "workspace.event_bus.bus",
        "workspace.event_bus.events",
        "workspace.event_bus.consumers",
        "workspace.event_bus.streams",
        "workspace.scheduler.dag_builder",
        "workspace.scheduler.dag_store",
        "workspace.scheduler.dispatcher",
        "workspace.scheduler.ci_handler",
        "workspace.scheduler.guardrail_enforcer",
        "workspace.scheduler.service",
        "workspace.skills_router.router",
        "workspace.memory.manager",
        "workspace.memory.flush",
    ),
)


def get_graph_blueprint() -> LangGraphBlueprint:
    """Return the declarative LangGraph architecture without creating a runnable graph."""

    return LANGGRAPH_BLUEPRINT


def build_graph(*_args, **_kwargs):
    raise NotImplementedError(
        "LangGraph execution pipeline is intentionally not implemented yet. "
        "This module currently exposes architecture only."
    )
