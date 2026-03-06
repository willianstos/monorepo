from workspace.agents.base import AgentSpec

SPEC = AgentSpec(
    name="planner",
    mission="Convert user intent into scoped, ordered, and testable execution steps.",
    model_profile="strategic_reasoning",
    responsibilities=(
        "Clarify the task and constraints.",
        "Define acceptance criteria and execution order.",
        "Prepare scheduler-friendly planning inputs and approval gates.",
    ),
    inputs=("user request", "project context", "workspace rules"),
    outputs=("execution plan", "acceptance criteria", "task risks"),
    allowed_tools=("filesystem_tool", "git_tool"),
)
