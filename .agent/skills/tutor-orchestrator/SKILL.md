---
name: tutor-orchestrator
description: Meta-skill for orchestrating Codex and Claude CLIs with advanced prompt engineering and real-time research.
---

# Tutor Orchestrator Skill

You are the brain behind the fingers. Use this skill to transform raw user intent into high-performance agent loops.

## AI Agent Ecosystem Knowledge
- **Codex CLI**: Best for context mapping (`.context`), MCP server management, and structural codebase understanding.
- **Claude Code CLI**: Best for logical implementation, large-scale refactoring, and terminal-agentic loops.
- **Tavily MCP**: Your window to the current state of AI. Use it to find:
    - Recent GitHub repos about "agentic coding".
    - Anthropic/Google/OpenAI blog posts on prompt engineering.
    - New MCP server releases.

## Prompt Engineering Framework
When generating a prompt for another agent, use the **M-T-S-V** structure:
1. **M**ission: Clear high-level goal.
2. **T**echnical Context: Which files to read, which KIs are relevant.
3. **S**trategy: Step-by-step logic (e.g., "First use browser, then use terminal").
4. **V**erification: How to prove the job is done (e.g., "Run npm test").

## Commands
### Research
- `tavily_search("current best practices for AI coding agents 2026")`
- `tavily_search("act_runner gitea docker network issues")`

### Context Setup
- `codex context build --target docs`
- `codex workflow-init --name "new-feat" --scale MEDIUM`

## Example Mission Briefing
```markdown
### 🚀 MISSION BRIEFING
**Goal**: Stabilize Gitea Runner.
**Context**: .runner file at /home/will/...
**Strategy**:
1. Check process status.
2. Verify connectivity to 172.17.0.1:3001.
3. Fix .runner if needed.
**Verification**: Check Gitea Admin UI.
```
