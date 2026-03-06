from workspace.agents.base import AgentSpec

SPEC = AgentSpec(
    name="reviewer",
    mission="Review change quality, correctness, security risk, and guardrail compliance.",
    model_profile="verification",
    responsibilities=(
        "Assess correctness and maintainability.",
        "Flag security, reliability, and policy risks.",
        "Approve, request changes, or block unsafe work.",
    ),
    inputs=("code changes", "test report", "issue context"),
    outputs=("review decision", "review notes", "risk log"),
    allowed_tools=("filesystem_tool", "git_tool"),
)
