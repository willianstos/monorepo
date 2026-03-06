from workspace.agents.base import AgentSpec

SPEC = AgentSpec(
    name="tester",
    mission="Own tests and fixtures and validate behavior for the change set.",
    model_profile="verification",
    responsibilities=(
        "Create or update tests and fixtures when required.",
        "Select and run appropriate validation checks.",
        "Capture failures, regressions, and coverage gaps.",
        "Return actionable feedback when validation fails.",
    ),
    inputs=("code changes", "test strategy", "project commands"),
    outputs=("test report", "quality decision", "test updates"),
    allowed_tools=("filesystem_tool", "terminal_tool", "git_tool"),
)
