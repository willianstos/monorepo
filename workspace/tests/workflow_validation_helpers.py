"""Shared helpers for workflow validation tests."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".agent" / "workflows"
WORKFLOW_FILES = ["git", "pr", "validate", "release-note", "workflow-map"]

ALLOWED_RUNNERS = {"wsl", "any", "cli"}
REQUIRED_METADATA_FIELDS = {"description", "trigger", "version"}
REQUIRED_SECTION_HEADINGS = [
    "what it is",
    "when to use",
    "run",
    "flow",
    "guardrails",
]

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
TRIGGER_RE = re.compile(r"^/[a-z0-9-]+$")
LINE_RE = re.compile(r"^(?P<key>[a-zA-Z_][a-zA-Z0-9_-]*)\s*:(?P<value>.*)$")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<title>.+?)\s*$")

DOCS = {
    "agents": REPO_ROOT / "AGENTS.md",
    "readme": REPO_ROOT / "README.md",
    "guardrails": REPO_ROOT / "GUARDRAILS.md",
    "workspace": REPO_ROOT / "WORKSPACE.md",
    "gitea": REPO_ROOT / "docs" / "gitea-pr-validation.md",
    "git_guide": REPO_ROOT / "docs" / "guide_git.md",
    "local_validation": REPO_ROOT / "docs" / "local-validation.md",
}


def workflow_path(name: str) -> Path:
    return WORKFLOWS_DIR / f"{name}.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def collect_workflow_headings(content: str) -> set[str]:
    return {
        normalize_heading(match.group("title"))
        for match in (HEADING_RE.match(line) for line in content.splitlines())
        if match
    }


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
        return value[1:-1].strip()
    return value


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    lines = content.splitlines()

    start_index: int | None = None
    for index, line in enumerate(lines[:12]):
        if line.strip() == "---":
            start_index = index
            break

    if start_index is None:
        raise AssertionError("Missing frontmatter delimiter '---' near top of file")

    end_index: int | None = None
    for index in range(start_index + 1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break

    if end_index is None:
        raise AssertionError("Frontmatter block missing closing delimiter '---'")

    frontmatter_lines = lines[start_index + 1 : end_index]
    metadata: dict[str, str] = {}

    for raw_line in frontmatter_lines:
        if not raw_line.strip():
            continue

        match = LINE_RE.match(raw_line)
        if not match:
            raise AssertionError(f"Invalid frontmatter line '{raw_line}'")

        key = match.group("key")
        value = _unquote(match.group("value"))
        if key in metadata:
            raise AssertionError(f"Duplicated frontmatter key '{key}'")
        if key != "args" and not value:
            raise AssertionError(f"Frontmatter key '{key}' has empty value")
        metadata[key] = value

    remainder = "\n".join(lines[end_index + 1 :])
    return metadata, remainder


def get_workflow_metadata(name: str) -> tuple[dict[str, str], str, Path]:
    path = workflow_path(name)
    content = read_text(path)
    metadata, body = parse_frontmatter(content)
    return metadata, body, path


def assert_required_frontmatter_fields(metadata: Mapping[str, str]) -> None:
    missing = REQUIRED_METADATA_FIELDS.difference(metadata)
    if missing:
        raise AssertionError(f"Missing required frontmatter fields: {sorted(missing)}")

    if not metadata["description"].strip():
        raise AssertionError("Frontmatter field 'description' must not be empty")
    if not TRIGGER_RE.match(metadata["trigger"].strip()):
        raise AssertionError("Frontmatter field 'trigger' must match '/<workflow-name>' format")
    if not VERSION_RE.match(metadata["version"].strip()):
        raise AssertionError("Frontmatter field 'version' must be semver-compatible")

    runner = metadata.get("runner")
    if runner is not None and runner not in ALLOWED_RUNNERS:
        raise AssertionError(
            f"Frontmatter field 'runner' has unsupported value '{runner}'. "
            f"Allowed values: {sorted(ALLOWED_RUNNERS)}"
        )


def assert_required_sections(body_text: str) -> None:
    headings = collect_workflow_headings(body_text)
    normalized_required = [normalize_heading(section) for section in REQUIRED_SECTION_HEADINGS]
    missing = [section for section in normalized_required if section not in headings]
    if missing:
        raise AssertionError(f"Missing required sections: {missing}")


def load_policy_corpus() -> dict[str, str]:
    return {name: read_text(path).lower() for name, path in DOCS.items()}


def contains_any(text: str, values: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(value.lower() in lowered for value in values)


def contains_phrase(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()
