"""Structure tests for canonical workflow documents."""

from __future__ import annotations

import pytest

from workspace.tests.workflow_validation_helpers import (
    REQUIRED_SECTION_HEADINGS,
    assert_required_frontmatter_fields,
    assert_required_sections,
    get_workflow_metadata,
    normalize_heading,
    workflow_path,
)


WORKFLOWS_IN_SCOPE = [
    "git",
    "pr",
    "validate",
    "release-note",
    "workflow-map",
]


@pytest.mark.parametrize("workflow_name", WORKFLOWS_IN_SCOPE)
def test_workflow_file_exists(workflow_name: str) -> None:
    assert workflow_path(workflow_name).exists(), f"Workflow file missing: {workflow_name}.md"


@pytest.mark.parametrize("workflow_name", WORKFLOWS_IN_SCOPE)
def test_workflow_metadata_is_structured(workflow_name: str) -> None:
    metadata, _body, path = get_workflow_metadata(workflow_name)

    assert_required_frontmatter_fields(metadata)

    expected_trigger = f"/{workflow_name}"
    assert metadata["trigger"] == expected_trigger, (
        f"{path.name} trigger must be '{expected_trigger}'"
    )

    if "runner" in metadata:
        runner = metadata["runner"]
        assert runner in {"wsl", "any", "cli"}


@pytest.mark.parametrize("workflow_name", WORKFLOWS_IN_SCOPE)
def test_workflow_sections_are_operational(workflow_name: str) -> None:
    _metadata, body, path = get_workflow_metadata(workflow_name)

    assert_required_sections(body)

    normalized_required = {normalize_heading(section) for section in REQUIRED_SECTION_HEADINGS}
    normalized_found = {
        normalize_heading(line.lstrip("#").strip())
        for line in body.splitlines()
        if line.lstrip().startswith("##")
    }

    missing = normalized_required.difference(normalized_found)
    assert not missing, f"{path.name} missing required sections: {sorted(missing)}"
