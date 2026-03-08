from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from workspace.tools import FilesystemTool, GitTool, TerminalTool, ToolPolicyError


REPO_ROOT = Path(__file__).resolve().parents[2]
NON_AUTHORITY_MARKERS = (
    "non-authoritative",
    "compatibility only",
    "compatibility pointer only",
    "compatibility pointer",
    "state, not policy",
    "not a policy authority",
    "historical evidence only",
    "historical planning snapshot",
    "compatibility and evidence only",
    "snapshot gerado. não autoritativo",
)


def _repo_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8").lower()


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


class FilesystemToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tempdir.name) / "repo"
        self.repo_root.mkdir()
        self.artifact_root = Path(self.tempdir.name) / ".context" / "tool-audit"
        (self.repo_root / "notes.txt").write_text("hello world", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_read_text_within_scope_records_artifact(self) -> None:
        tool = FilesystemTool(root=self.repo_root, artifact_root=self.artifact_root)

        content = tool.read_text("notes.txt")

        self.assertEqual(content, "hello world")
        artifacts = list((self.artifact_root / "filesystem_tool").glob("*.json"))
        self.assertEqual(len(artifacts), 1)

    def test_write_text_outside_scope_is_rejected_and_audited(self) -> None:
        tool = FilesystemTool(root=self.repo_root, artifact_root=self.artifact_root)

        with self.assertRaises(ToolPolicyError):
            tool.write_text("../escape.txt", "nope")

        artifacts = list((self.artifact_root / "filesystem_tool").glob("*.json"))
        self.assertEqual(len(artifacts), 1)
        payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "rejected")


class TerminalToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.artifact_root = Path(self.tempdir.name) / ".context" / "tool-audit"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_allowlisted_command_runs_and_records_artifact(self) -> None:
        tool = TerminalTool(
            allowed_commands=["git"],
            working_directory=Path(self.tempdir.name),
            artifact_root=self.artifact_root,
        )

        output = tool.run("git --version")

        self.assertIn("git version", output)
        artifacts = list((self.artifact_root / "terminal_tool").glob("*.json"))
        self.assertEqual(len(artifacts), 1)

    def test_shell_chaining_is_rejected_and_audited(self) -> None:
        tool = TerminalTool(
            allowed_commands=["git"],
            working_directory=Path(self.tempdir.name),
            artifact_root=self.artifact_root,
        )

        with self.assertRaises(ToolPolicyError):
            tool.run("git --version && whoami")

        artifacts = list((self.artifact_root / "terminal_tool").glob("*.json"))
        self.assertEqual(len(artifacts), 1)
        payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "rejected")


class GitToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tempdir.name) / "repo"
        self.repo_root.mkdir()
        self.artifact_root = Path(self.tempdir.name) / ".context" / "tool-audit"
        subprocess.run(
            ["git", "init"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=True,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_status_records_artifact(self) -> None:
        tool = GitTool(repo_root=self.repo_root, artifact_root=self.artifact_root)

        output = tool.status()

        self.assertEqual(output, "")
        artifacts = list((self.artifact_root / "git_tool").glob("*.json"))
        self.assertEqual(len(artifacts), 1)


class AuthorityHierarchyTests(unittest.TestCase):
    def test_required_canonical_layers_exist(self) -> None:
        required_paths = [
            "AGENTS.md",
            ".agent/rules",
            ".agent/workflows",
            ".agent/skills",
            ".claude",
            ".context/workflow",
            "docs/authority-hierarchy.md",
        ]

        for relative_path in required_paths:
            with self.subTest(path=relative_path):
                self.assertTrue(
                    (REPO_ROOT / relative_path).exists(),
                    f"Missing canonical authority layer: {relative_path}",
                )

    def test_agents_declares_the_frozen_authority_hierarchy(self) -> None:
        text = _repo_text("AGENTS.md")
        required_phrases = [
            "single global repository contract",
            "hierarchy is frozen",
            "operational rules: `.agent/rules/`",
            "workflows: `.agent/workflows/`",
            "skills: `.agent/skills/`",
            "claude-specific extensions: `.claude/`",
            "`.context/` is state and evidence only",
            "legacy and tool-specific files are compatibility pointers only",
        ]

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_layer_documents_preserve_authority_roles(self) -> None:
        expectations = {
            ".agent/rules/README.md": (
                "shared operator rules",
                "full repository contract remains [`agents.md`]",
            ),
            ".agent/workflows/README.md": (
                "execution playbooks",
                "not the repository contract",
            ),
            ".agent/skills/README.md": (
                "capability assets only",
                "no repository policy or workflow authority",
            ),
            ".claude/CLAUDE.md": (
                "claude-specific extension only",
                "non-authoritative relative to [`agents.md`]",
            ),
            ".context/workflow/README.md": (
                "non-authoritative",
                "state, not policy",
            ),
        }

        for relative_path, phrases in expectations.items():
            text = _repo_text(relative_path)
            for phrase in phrases:
                with self.subTest(path=relative_path, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_contributing_includes_authority_freeze_checklist(self) -> None:
        text = _repo_text("CONTRIBUTING.md")

        required_phrases = [
            "authority freeze checklist",
            "no new competing instruction source was created",
            "operational rules stay in `.agent/rules/`",
            "workflow logic stays in `.agent/workflows/`",
            "`.context/` was not turned into policy authority",
            "explicitly non-authoritative and points to the canonical source",
            "flagged for human review in the pr",
        ]

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        forbidden_phrases = [
            "edit `.context/` indexes when adding new reusable documentation or agent playbooks",
            "link new long-lived guidance from `.context/docs/README.md`",
            "link new reusable agent instructions from `.context/agents/README.md`",
        ]

        for phrase in forbidden_phrases:
            with self.subTest(forbidden=phrase):
                self.assertNotIn(phrase, text)

    def test_context_entrypoints_are_explicitly_non_authoritative(self) -> None:
        context_files = [
            REPO_ROOT / ".context" / "agents" / "README.md",
            REPO_ROOT / ".context" / "skills" / "README.md",
            REPO_ROOT / ".context" / "docs" / "README.md",
            REPO_ROOT / ".context" / "docs" / "qa" / "README.md",
            REPO_ROOT / ".context" / "plans" / "README.md",
            REPO_ROOT / ".context" / "plans" / "future-agents-evolution-2026.md",
            REPO_ROOT / ".context" / "workflow" / "README.md",
            REPO_ROOT / ".context" / "walkthrough.md",
        ]
        context_files.extend(sorted((REPO_ROOT / ".context" / "docs").glob("*.md")))

        for path in context_files:
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=relative_path):
                self.assertTrue(
                    _contains_any(text, NON_AUTHORITY_MARKERS),
                    f"{relative_path} must state that it is non-authoritative",
                )

    def test_legacy_compatibility_files_are_explicit_pointers(self) -> None:
        legacy_files = [
            "CLAUDE.md",
            ".claude/instructions/README.md",
        ]

        for relative_path in legacy_files:
            text = _repo_text(relative_path)
            with self.subTest(path=relative_path):
                self.assertTrue(
                    _contains_any(text, NON_AUTHORITY_MARKERS),
                    f"{relative_path} must be marked as compatibility-only or non-authoritative",
                )
                self.assertIn("agents.md", text)

    def test_hidden_ide_instruction_files_must_not_be_canonical(self) -> None:
        candidate_paths = [
            REPO_ROOT / ".cursorrules",
            REPO_ROOT / ".cursor" / "rules",
            REPO_ROOT / ".cursor" / "instructions.md",
            REPO_ROOT / ".windsurfrules",
            REPO_ROOT / ".windsurf" / "rules",
            REPO_ROOT / ".github" / "copilot-instructions.md",
            REPO_ROOT / ".github" / "instructions",
        ]

        files_to_check: list[Path] = []
        for candidate in candidate_paths:
            if candidate.is_file():
                files_to_check.append(candidate)
            elif candidate.is_dir():
                files_to_check.extend(
                    path
                    for path in candidate.rglob("*")
                    if path.is_file() and path.suffix.lower() in {".md", ".mdc", ".txt"}
                )

        for path in files_to_check:
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=relative_path):
                self.assertTrue(
                    _contains_any(text, NON_AUTHORITY_MARKERS),
                    f"{relative_path} must be marked as non-authoritative",
                )
                self.assertIn("agents.md", text)

    def test_git_authority_chain_remains_pinned(self) -> None:
        agents = _repo_text("AGENTS.md")
        guide = _repo_text("docs/guide_git.md")
        workflow = _repo_text(".agent/workflows/git.md")
        gitea = _repo_text("docs/gitea-pr-validation.md")

        self.assertIn("merge to `main`: requires human approval after ci passes", agents)
        self.assertIn("`main` é a branch protegida e canônica", guide)
        self.assertIn("gitea", guide)
        self.assertIn("autoritativo", guide)
        self.assertIn("github", guide)
        self.assertIn("espelho somente", guide)
        self.assertIn("/git", guide)
        self.assertIn("não abre pr", guide)
        self.assertIn("não substitui revisão, ci ou aprovação humana", guide)
        self.assertIn("does not replace the pr gate", workflow)
        self.assertIn("gitea", workflow)
        self.assertIn("github mirror", workflow)
        self.assertIn("authoritative host", gitea)
        self.assertIn("github is mirror-only", gitea)
        self.assertIn(
            "no merge without both passing ci and explicit human approval",
            gitea,
        )
        self.assertIn("feature branch  ->  pr to main  ->  ci green  ->  human approval  ->  merge", gitea)

    def test_authority_hierarchy_doc_is_subordinate_and_review_gated(self) -> None:
        text = _repo_text("docs/authority-hierarchy.md")

        self.assertIn("agents.md", text)
        self.assertIn("single global contract", text)
        self.assertIn("requires explicit human review in a pr", text)


if __name__ == "__main__":
    unittest.main()
