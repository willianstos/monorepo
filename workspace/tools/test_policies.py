from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from workspace.tools import FilesystemTool, GitTool, TerminalTool, ToolPolicyError


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


if __name__ == "__main__":
    unittest.main()
