from __future__ import annotations

import json
from pathlib import Path

from workspace.mcp.config_registry import MCPRegistry


def make_temp_registry(tmp_path: Path) -> MCPRegistry:
    repo_root = Path(__file__).resolve().parents[2]
    registry_src = repo_root / "bootstrap" / "mcp-registry.toml"
    bootstrap_dir = tmp_path / "bootstrap"
    env_dir = tmp_path / "env"
    bootstrap_dir.mkdir()
    env_dir.mkdir()
    (bootstrap_dir / "mcp-registry.toml").write_text(registry_src.read_text(encoding="utf-8"), encoding="utf-8")
    return MCPRegistry(bootstrap_dir / "mcp-registry.toml", repo_root=tmp_path)


def test_codex_wsl_template_renders_factory_inventory_without_inline_secrets() -> None:
    registry = MCPRegistry.from_default()

    rendered = registry.render_template("codex_wsl")

    assert rendered.count("[mcp_servers.") == 11
    assert "ctx7sk-" not in rendered
    assert "tvly-dev-" not in rendered
    assert "sk-user-" not in rendered


def test_registry_renders_target_specific_transport_overrides() -> None:
    registry = MCPRegistry.from_default()

    wsl = registry.render_template("codex_wsl")
    windows = registry.render_template("codex_windows_toml")

    assert 'command = "uvx"' in wsl
    assert 'args = ["mcp-server-fetch==2025.4.7"]' in wsl
    assert 'command = "wsl.exe"' in windows
    assert 'mcp-launch-future-agents.sh' in windows
    assert 'args = ["-y", "mcp-server-fetch"]' in windows


def test_live_render_uses_secret_overlay_for_codex_toml(tmp_path: Path) -> None:
    registry = make_temp_registry(tmp_path)
    repo_root = registry.repo_root
    (repo_root / "codex_secrets.toml").write_text(
        """
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp@2.1.2"]
env = { CONTEXT7_API_KEY = "test-context7" }
""".strip()
        + "\n",
        encoding="utf-8",
    )

    rendered = registry.render_live("codex_wsl")

    assert 'CONTEXT7_API_KEY = "test-context7"' in rendered
    assert "test-context7" not in registry.render_template("codex_wsl")


def test_project_profile_binds_filesystem_server_to_project_root(tmp_path: Path) -> None:
    registry = make_temp_registry(tmp_path)

    desired = registry.desired_server_entries(
        "project_mcp",
        include_secrets=False,
        project_root=Path("/tmp/example-project"),
    )

    assert desired["filesystem"]["args"][-1] == "/tmp/example-project"


def test_json_apply_preserves_unknown_top_level_and_server_fields(tmp_path: Path) -> None:
    registry = make_temp_registry(tmp_path)
    target = tmp_path / "claude_desktop_config.json"
    target.write_text(
        json.dumps(
            {
                "theme": "system",
                "mcpServers": {
                    "chrome-devtools": {
                        "startupTimeout": 60,
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    registry.apply_target("claude_desktop", target, check_only=False)
    applied = json.loads(target.read_text(encoding="utf-8"))

    assert applied["theme"] == "system"
    assert applied["mcpServers"]["chrome-devtools"]["startupTimeout"] == 60
    assert applied["mcpServers"]["chrome-devtools"]["command"] == "npx"
