"""Single-source MCP registry loading, rendering, and governance helpers."""

from __future__ import annotations

import json
import os
import re
import shutil
import tomllib
from hashlib import sha256
from pathlib import Path
from typing import Any

PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")
JSON_TARGETS = {"claude_desktop", "codex_windows_json", "project_mcp"}


class MCPRegistry:
    """Loads the canonical MCP registry and renders target-specific config."""

    def __init__(self, registry_path: Path, repo_root: Path | None = None) -> None:
        self.registry_path = registry_path.resolve()
        self.repo_root = (repo_root or self.registry_path.parent.parent).resolve()
        self.data = tomllib.loads(self.registry_path.read_text(encoding="utf-8"))

    @classmethod
    def from_default(cls) -> "MCPRegistry":
        root = Path(__file__).resolve().parents[2]
        return cls(root / "bootstrap" / "mcp-registry.toml", repo_root=root)

    def template_targets(self) -> list[str]:
        return list(self.data["targets"].keys())

    def target_output_path(self, target_name: str) -> Path:
        return self.repo_root / self.data["targets"][target_name]["output"]

    def render_template(self, target_name: str) -> str:
        if self.target_format(target_name) == "codex_toml":
            return self.render_codex_toml(target_name, include_secrets=False)
        return self.render_json_fragment(target_name, include_secrets=False)

    def render_live(self, target_name: str, existing_path: Path | None = None) -> str:
        if self.target_format(target_name) == "codex_toml":
            return self.render_codex_toml(target_name, include_secrets=True, existing_path=existing_path)
        return self.render_json_fragment(target_name, include_secrets=True, existing_path=existing_path)

    def target_format(self, target_name: str) -> str:
        return self.data["targets"][target_name]["format"]

    def profile_servers(self, target_name: str) -> list[str]:
        profile = self.data["targets"][target_name]["profile"]
        return list(self.data["profiles"][profile]["servers"])

    def codex_context(self, target_name: str) -> dict[str, Any]:
        paths = self.data["paths"]
        codex = self.data["codex"]
        platform_key = "wsl" if target_name == "codex_wsl" else "windows"
        return {
            "personality": codex["personality"],
            "model": codex["model"],
            "model_reasoning_effort": codex["model_reasoning_effort"],
            "projects_base": paths[f"projects_base_{platform_key}"],
            "codex_include": paths[f"codex_include_{platform_key}"],
            "trusted_projects": codex["trusted_projects"][platform_key]["paths"],
            "hide_full_access_warning": codex["hide_full_access_warning"],
            "model_migrations": codex["model_migrations"],
            "model_availability_nux": codex["model_availability_nux"],
        }

    def render_codex_toml(
        self,
        target_name: str,
        *,
        include_secrets: bool,
        existing_path: Path | None = None,
    ) -> str:
        if target_name not in {"codex_wsl", "codex_windows_toml"}:
            raise ValueError(f"{target_name} is not a Codex TOML target")
        context = self.codex_context(target_name)
        rendered_servers, warnings = self._render_servers(
            target_name,
            include_secrets=include_secrets,
            existing_path=existing_path,
        )
        header = [
            "# Generated from bootstrap/mcp-registry.toml.",
            "# Edit the registry, not this file.",
            "",
            f'personality = {self._toml_scalar(context["personality"])}',
            f'model = {self._toml_scalar(context["model"])}',
            f'model_reasoning_effort = {self._toml_scalar(context["model_reasoning_effort"])}',
            "",
            "[core]",
            f'projectsBase = {self._toml_scalar(context["projects_base"])}',
            "",
            "[mcp]",
            "enabled = true",
            f'include = {self._toml_scalar(context["codex_include"])}',
            "",
        ]
        for path in context["trusted_projects"]:
            header.extend(
                [
                    f'[projects.{self._quoted_table_key(path)}]',
                    'trust_level = "trusted"',
                    "",
                ]
            )
        header.extend(
            [
                "[notice]",
                f'hide_full_access_warning = {self._toml_scalar(context["hide_full_access_warning"])}',
                "",
                "[notice.model_migrations]",
            ]
        )
        for key, value in context["model_migrations"].items():
            header.append(f"{key} = {self._toml_scalar(value)}")
        header.extend(["", "[tui.model_availability_nux]"])
        for key, value in context["model_availability_nux"].items():
            header.append(f"{self._toml_scalar(key)} = {self._toml_scalar(value)}")
        blocks = header + [""]
        for name in self.profile_servers(target_name):
            server = rendered_servers[name]
            note = warnings.get(name)
            if note:
                blocks.append(f"# {note}")
            blocks.append(f"[mcp_servers.{self._quoted_table_key(name)}]")
            blocks.append(f'command = {self._toml_scalar(server["command"])}')
            blocks.append(f"args = {self._toml_array(server['args'])}")
            if "env" in server and server["env"]:
                blocks.append(f"env = {self._toml_inline_table(server['env'])}")
            blocks.append(f"startup_timeout_sec = {server['startup_timeout_sec']}")
            blocks.append("")
        return "\n".join(blocks).rstrip() + "\n"

    def render_json_fragment(
        self,
        target_name: str,
        *,
        include_secrets: bool,
        existing_path: Path | None = None,
        project_root: Path | None = None,
    ) -> str:
        servers, _ = self._render_servers(
            target_name,
            include_secrets=include_secrets,
            existing_path=existing_path,
            project_root=project_root,
        )
        payload = {"mcpServers": servers}
        return json.dumps(payload, indent=2) + "\n"

    def desired_server_entries(
        self,
        target_name: str,
        *,
        include_secrets: bool,
        existing_path: Path | None = None,
        project_root: Path | None = None,
    ) -> dict[str, dict[str, Any]]:
        servers, _ = self._render_servers(
            target_name,
            include_secrets=include_secrets,
            existing_path=existing_path,
            project_root=project_root,
        )
        return servers

    def render_templates(self, targets: list[str] | None = None) -> list[Path]:
        rendered = []
        for target_name in targets or self.template_targets():
            output_path = self.target_output_path(target_name)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            content = self.render_template(target_name)
            output_path.write_text(content, encoding="utf-8", newline="\n")
            rendered.append(output_path)
        return rendered

    def apply_target(
        self,
        target_name: str,
        output_path: Path,
        *,
        manifest_path: Path | None = None,
        check_only: bool = False,
    ) -> list[str]:
        output_path = output_path.expanduser()
        if self.target_format(target_name) == "codex_toml":
            content = self.render_live(target_name, existing_path=output_path)
            return self._apply_text_target(
                target_name,
                output_path,
                content,
                manifest_path=manifest_path,
                check_only=check_only,
            )

        desired = self.desired_server_entries(
            target_name,
            include_secrets=True,
            existing_path=output_path,
        )
        return self._apply_json_target(
            target_name,
            output_path,
            desired,
            manifest_path=manifest_path,
            check_only=check_only,
        )

    def apply_project_tree(self, projects_root: Path, *, check_only: bool = False) -> list[str]:
        projects_root = projects_root.expanduser()
        messages: list[str] = []
        files = sorted(
            path
            for path in projects_root.rglob(".mcp.json")
            if ".git" not in path.parts and "node_modules" not in path.parts
        )
        if not files:
            return [f"[skip] No .mcp.json files found under {projects_root}"]
        for file_path in files:
            desired = self.desired_server_entries(
                "project_mcp",
                include_secrets=True,
                existing_path=file_path,
                project_root=file_path.parent,
            )
            messages.extend(
                self._apply_json_target(
                    "project_mcp",
                    file_path,
                    desired,
                    manifest_path=None,
                    check_only=check_only,
                )
            )
        return messages

    def _apply_text_target(
        self,
        target_name: str,
        output_path: Path,
        content: str,
        *,
        manifest_path: Path | None,
        check_only: bool,
    ) -> list[str]:
        messages: list[str] = []
        expected_hash = sha256(content.encode("utf-8")).hexdigest()
        if check_only:
            if not output_path.exists():
                raise FileNotFoundError(f"Managed target missing: {output_path}")
            actual_text = output_path.read_text(encoding="utf-8")
            actual_hash = sha256(actual_text.encode("utf-8")).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Drift detected for {output_path} (expected {expected_hash}, actual {actual_hash})"
                )
            messages.append(f"[ok] Drift check passed: {output_path}")
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.exists() and output_path.read_text(encoding="utf-8") == content:
                messages.append(f"[ok] Already aligned: {output_path}")
            else:
                self._backup_if_needed(output_path)
                output_path.write_text(content, encoding="utf-8", newline="\n")
                messages.append(f"[ok] Applied managed {target_name} config to {output_path}")
        if manifest_path is not None:
            self._write_manifest(
                manifest_path.expanduser(),
                target_name=target_name,
                target_path=output_path,
                sha256_hash=expected_hash,
                mode="check" if check_only else "apply",
            )
        return messages

    def _apply_json_target(
        self,
        target_name: str,
        output_path: Path,
        desired_servers: dict[str, dict[str, Any]],
        *,
        manifest_path: Path | None,
        check_only: bool,
    ) -> list[str]:
        current = {}
        if output_path.exists():
            current = json.loads(output_path.read_text(encoding="utf-8"))
        current_servers = current.setdefault("mcpServers", {})
        messages: list[str] = []
        changed = False
        for name, desired in desired_servers.items():
            existing = current_servers.get(name, {})
            merged = self._merge_server_entry(existing, desired)
            if existing != merged:
                changed = True
            current_servers[name] = merged
        rendered = json.dumps(current, indent=2) + "\n"
        expected_hash = sha256(rendered.encode("utf-8")).hexdigest()
        if check_only:
            if not output_path.exists():
                raise FileNotFoundError(f"Managed target missing: {output_path}")
            actual = json.loads(output_path.read_text(encoding="utf-8"))
            actual_servers = actual.get("mcpServers", {})
            for name, desired in desired_servers.items():
                if self._merge_server_entry(actual_servers.get(name, {}), desired) != actual_servers.get(name, {}):
                    raise ValueError(f"Drift detected for {output_path} in mcpServers.{name}")
            messages.append(f"[ok] Drift check passed: {output_path}")
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.exists() and output_path.read_text(encoding="utf-8") == rendered:
                messages.append(f"[ok] Already aligned: {output_path}")
            else:
                self._backup_if_needed(output_path)
                output_path.write_text(rendered, encoding="utf-8", newline="\n")
                changed = True
                messages.append(f"[ok] Applied managed {target_name} config to {output_path}")
            if not changed:
                messages[-1] = f"[ok] Already aligned: {output_path}"
        if manifest_path is not None:
            self._write_manifest(
                manifest_path.expanduser(),
                target_name=target_name,
                target_path=output_path,
                sha256_hash=expected_hash,
                mode="check" if check_only else "apply",
            )
        return messages

    def _merge_server_entry(
        self, existing: dict[str, Any], desired: dict[str, Any]
    ) -> dict[str, Any]:
        merged = dict(existing)
        for key, value in desired.items():
            if key == "env":
                env = dict(existing.get("env", {}))
                env.update(value)
                merged["env"] = env
                continue
            merged[key] = value
        return merged

    def _render_servers(
        self,
        target_name: str,
        *,
        include_secrets: bool,
        existing_path: Path | None = None,
        project_root: Path | None = None,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
        context = dict(self.data["paths"])
        if project_root is not None:
            context["project_root"] = str(project_root)
        elif target_name == "project_mcp":
            context["project_root"] = "__PROJECT_ROOT__"
        existing_server_envs = self._extract_server_envs(existing_path)
        env_layers = self._load_env_layers()
        secret_server_layers = self._load_secret_server_layers(target_name)
        rendered: dict[str, dict[str, Any]] = {}
        warnings: dict[str, str] = {}
        for name in self.profile_servers(target_name):
            spec = self.data["servers"][name]
            surface = spec["surfaces"][target_name]
            entry: dict[str, Any] = {
                "command": self._substitute(surface["command"], context),
                "args": self._substitute(surface["args"], context),
            }
            env_map: dict[str, str] = {}
            env_map.update(self._substitute(surface.get("env", {}), context))
            for env_key in surface.get("runtime_env_keys", []):
                value = os.environ.get(env_key) or existing_server_envs.get(name, {}).get(env_key)
                if value:
                    env_map[env_key] = value
            if include_secrets:
                for config_key, candidates in spec.get("secret_env_candidates", {}).items():
                    value = self._resolve_secret_value(
                        server_name=name,
                        output_key=config_key,
                        candidates=candidates,
                        env_layers=env_layers,
                        server_layers=secret_server_layers,
                        existing_env=existing_server_envs.get(name, {}),
                    )
                    if value:
                        env_map[config_key] = value
                    else:
                        warnings[name] = spec.get("template_note", "Secret env not resolved.")
            elif spec.get("secret_env_candidates"):
                warnings[name] = spec.get("template_note", "Secret env not resolved.")
            if env_map:
                entry["env"] = env_map
            if target_name in {"codex_wsl", "codex_windows_toml", "codex_windows_json"}:
                entry["startup_timeout_sec"] = int(spec["startup_timeout_sec"])
            rendered[name] = entry
        return rendered, warnings

    def _extract_server_envs(self, path: Path | None) -> dict[str, dict[str, str]]:
        if path is None or not path.exists():
            return {}
        try:
            if path.suffix == ".toml":
                parsed = tomllib.loads(path.read_text(encoding="utf-8"))
            else:
                parsed = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        servers = parsed.get("mcp_servers") or parsed.get("mcpServers") or {}
        envs: dict[str, dict[str, str]] = {}
        for name, config in servers.items():
            if isinstance(config, dict) and isinstance(config.get("env"), dict):
                envs[name] = {
                    key: value
                    for key, value in config["env"].items()
                    if isinstance(value, str) and value
                }
        return envs

    def _load_env_layers(self) -> list[dict[str, str]]:
        layers = [{key: value for key, value in os.environ.items() if value}]
        dotenv_path = self.repo_root / "env" / ".env"
        if dotenv_path.exists():
            layers.append(self._parse_dotenv(dotenv_path))
        return layers

    def _load_secret_server_layers(self, target_name: str) -> list[dict[str, dict[str, str]]]:
        mappings = {
            "codex_wsl": ["codex_secrets.toml", "codex_secrets.json", "codex_wsl_secrets.json"],
            "codex_windows_toml": ["codex_secrets.toml", "codex_secrets.json"],
            "codex_windows_json": ["codex_secrets.json"],
            "claude_desktop": ["claude_secrets.json"],
            "project_mcp": [],
        }
        layers = []
        for relative in mappings[target_name]:
            file_path = self.repo_root / relative
            if file_path.exists():
                layers.append(self._extract_server_envs(file_path))
        return layers

    def _resolve_secret_value(
        self,
        *,
        server_name: str,
        output_key: str,
        candidates: list[str],
        env_layers: list[dict[str, str]],
        server_layers: list[dict[str, dict[str, str]]],
        existing_env: dict[str, str],
    ) -> str | None:
        search_keys = [output_key, *candidates]
        for layer in env_layers:
            for key in search_keys:
                value = layer.get(key)
                if value:
                    return value
        for layer in server_layers:
            for key in search_keys:
                value = layer.get(server_name, {}).get(key)
                if value:
                    return value
        for key in search_keys:
            value = existing_env.get(key)
            if value:
                return value
        return None

    def _substitute(self, value: Any, context: dict[str, Any]) -> Any:
        if isinstance(value, str):
            return PLACEHOLDER_RE.sub(lambda match: str(context[match.group(1)]), value)
        if isinstance(value, list):
            return [self._substitute(item, context) for item in value]
        if isinstance(value, dict):
            return {key: self._substitute(item, context) for key, item in value.items()}
        return value

    def _parse_dotenv(self, path: Path) -> dict[str, str]:
        values: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value:
                values[key] = value
        return values

    def _backup_if_needed(self, path: Path) -> None:
        if path.exists():
            backup = path.with_name(f"{path.name}.bak.{self._timestamp()}")
            shutil.copy2(path, backup)

    def _write_manifest(
        self,
        manifest_path: Path,
        *,
        target_name: str,
        target_path: Path,
        sha256_hash: str,
        mode: str,
    ) -> None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "managed_by": "bootstrap/render_mcp_configs.py",
            "registry": str(self.registry_path),
            "target": target_name,
            "target_path": str(target_path),
            "sha256": sha256_hash,
            "mode": mode,
        }
        manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")

    def _timestamp(self) -> str:
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d-%H%M%S")

    def _quoted_table_key(self, value: str) -> str:
        return json.dumps(value)

    def _toml_scalar(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return str(value)
        return json.dumps(value)

    def _toml_array(self, values: list[Any]) -> str:
        return "[" + ", ".join(self._toml_scalar(value) for value in values) + "]"

    def _toml_inline_table(self, values: dict[str, Any]) -> str:
        return "{ " + ", ".join(f"{key} = {self._toml_scalar(value)}" for key, value in values.items()) + " }"
