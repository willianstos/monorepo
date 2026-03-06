from workspace.agents.base import AgentSpec

SPEC = AgentSpec(
    name="coder",
    mission="Apply implementation changes that satisfy the approved plan and repository constraints.",
    model_profile="implementation",
    responsibilities=(
        "Modify implementation code only within approved project scope.",
        "Avoid tests, fixtures, and CI configuration.",
        "Record changed files and implementation notes.",
        "Prepare artifacts for testing and review.",
    ),
    inputs=("execution plan", "repository context", "selected project files"),
    outputs=("code changes", "change summary", "implementation notes"),
    allowed_tools=("filesystem_tool", "git_tool", "terminal_tool"),
)
