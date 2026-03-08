#!/usr/bin/env python3
"""Render and apply MCP configs from the canonical registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.mcp.config_registry import MCPRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    templates = subparsers.add_parser("templates", help="Render repo-managed templates.")
    templates.add_argument("--target", action="append", dest="targets", help="Target name to render.")

    for name in ("apply", "check"):
        cmd = subparsers.add_parser(name, help=f"{name.title()} a managed MCP target.")
        cmd.add_argument("--target", required=True, help="Target name from bootstrap/mcp-registry.toml.")
        cmd.add_argument("--output", help="Live output path for the target.")
        cmd.add_argument("--manifest", help="Optional manifest path for drift records.")
        cmd.add_argument("--projects-root", help="Root path used for project_mcp discovery.")
    return parser


def default_output_for(target: str) -> str | None:
    if target == "codex_wsl":
        return str(Path.home() / ".codex" / "config.toml")
    if target == "codex_windows_toml":
        userprofile = Path.home()
        return str(userprofile / ".codex" / "config.toml")
    if target == "codex_windows_json":
        userprofile = Path.home()
        return str(userprofile / ".codex" / "config.json")
    if target == "claude_desktop":
        appdata = Path(
            Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        )
        return str(appdata)
    return None


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    registry = MCPRegistry.from_default()

    if args.command == "templates":
        for output in registry.render_templates(args.targets):
            print(f"[ok] Rendered template {output}")
        return 0

    target = args.target
    if target == "project_mcp":
        if not args.projects_root:
            parser.error("--projects-root is required for project_mcp")
        messages = registry.apply_project_tree(
            Path(args.projects_root),
            check_only=args.command == "check",
        )
        for message in messages:
            print(message)
        return 0

    output_arg = args.output or default_output_for(target)
    if output_arg is None:
        parser.error(f"--output is required for target {target}")
    manifest = Path(args.manifest).expanduser() if args.manifest else None
    messages = registry.apply_target(
        target,
        Path(output_arg),
        manifest_path=manifest,
        check_only=args.command == "check",
    )
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
