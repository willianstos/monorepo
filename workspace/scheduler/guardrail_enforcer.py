from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workspace.event_bus import AgentEvent
from workspace.scheduler.dag_builder import TaskGraph, TaskNode, TaskStatus

GUARDRAIL_RULE_FILES: tuple[str, ...] = (
    "global.rules",
    "planner.rules",
    "coder.rules",
    "tester.rules",
    "reviewer.rules",
    "ci.rules",
    "security.rules",
)

ALLOWED_STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("ready", "blocked", "cancelled"),
    "ready": ("running", "blocked", "cancelled"),
    "running": ("completed", "failed", "blocked", "cancelled"),
    "blocked": ("ready", "pending", "cancelled"),
    "failed": ("ready", "cancelled"),
    "completed": (),
    "cancelled": (),
}

TASK_ASSIGNMENT_RULES: dict[str, str] = {
    "plan_task": "planner",
    "implement_task": "coder",
    "fix_task": "coder",
    "test_task": "tester",
    "review_task": "reviewer",
    "human_approval_gate": "system",
    "merge_task": "system",
    "rerun_ci": "system",
}

RAW_MEMORY_FIELDS: tuple[str, ...] = (
    "conversation",
    "conversations",
    "messages",
    "raw_conversation",
    "raw_messages",
    "transcript",
)


@dataclass(frozen=True)
class GuardrailViolation:
    rule: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"rule": self.rule, "message": self.message}


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    violations: tuple[GuardrailViolation, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "violations": [violation.to_dict() for violation in self.violations],
        }


class GuardrailEnforcer:
    """Evaluate scheduler dispatch and result events against repository guardrails."""

    def __init__(self, rules_root: Path | None = None) -> None:
        self.rules_root = rules_root or Path("guardrails")

    def load_rule_text(self) -> dict[str, str]:
        if not self.rules_root.exists():
            return {}
        return {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(self.rules_root.glob("*.rules"))
        }

    def missing_rule_files(self) -> list[str]:
        loaded_rules = self.load_rule_text()
        return [rule_name for rule_name in GUARDRAIL_RULE_FILES if rule_name not in loaded_rules]

    def describe(self) -> dict[str, Any]:
        return {
            "rules_root": str(self.rules_root),
            "rule_files": list(GUARDRAIL_RULE_FILES),
            "loaded_rules": sorted(self.load_rule_text().keys()),
            "missing_rules": self.missing_rule_files(),
            "ci_is_authoritative": True,
            "direct_agent_calls_forbidden": True,
            "merge_requires_human_approval": True,
            "status_transitions": ALLOWED_STATUS_TRANSITIONS,
        }

    def validate_dispatch(self, task: TaskNode, graph: TaskGraph) -> GuardrailDecision:
        violations: list[GuardrailViolation] = []
        violations.extend(self._missing_rules_violations())

        if task.guardrail_policy.get("allow_direct_agent_calls", False):
            violations.append(
                GuardrailViolation(
                    rule="direct_agent_calls",
                    message="Tasks may only be dispatched through Redis Streams.",
                )
            )

        expected_assignee = TASK_ASSIGNMENT_RULES.get(task.task_type)
        if expected_assignee and task.assigned_agent != expected_assignee:
            violations.append(self._ownership_violation(task, expected=expected_assignee))

        if task.status != "ready":
            violations.append(
                GuardrailViolation(
                    rule="dispatch_transition",
                    message=f"Task '{task.task_id}' must be ready before dispatch.",
                )
            )

        if task.guardrail_policy.get("requires_ci_pass") and graph.ci_status != "passed":
            violations.append(
                GuardrailViolation(
                    rule="ci_authority",
                    message=f"Task '{task.task_id}' is blocked until CI passes.",
                )
            )

        if task.task_type == "merge_task" and graph.metadata.get("human_approval_status") != "approved":
            violations.append(
                GuardrailViolation(
                    rule="human_approval",
                    message="Merge may not proceed without recorded human approval.",
                )
            )

        if graph.ci_status in {"failed", "coverage_failed", "security_failed"} and task.task_type in {
            "review_task",
            "human_approval_gate",
            "merge_task",
        }:
            violations.append(
                GuardrailViolation(
                    rule="ci_failed_block",
                    message=f"Task '{task.task_id}' is blocked while CI status is '{graph.ci_status}'.",
                )
            )

        return GuardrailDecision(allowed=not violations, violations=tuple(violations))

    def validate_result(self, task: TaskNode, event: AgentEvent) -> GuardrailDecision:
        violations: list[GuardrailViolation] = []
        violations.extend(self._missing_rules_violations())
        payload = event.payload

        if payload.get("direct_agent_call"):
            violations.append(
                GuardrailViolation(
                    rule="direct_agent_calls",
                    message="Results may not claim direct agent-to-agent coordination.",
                )
            )

        changed_files = [str(path) for path in payload.get("changed_files", [])]
        if task.assigned_agent == "coder":
            if any(self._is_test_path(path) for path in changed_files):
                violations.append(
                    GuardrailViolation(
                        rule="coder_test_boundary",
                        message="Coder results may not modify test files.",
                    )
                )
            if any(self._is_ci_path(path) for path in changed_files):
                violations.append(
                    GuardrailViolation(
                        rule="coder_ci_boundary",
                        message="Coder results may not modify CI configuration.",
                    )
                )

        if task.assigned_agent == "tester":
            non_test_paths = [
                path for path in changed_files if not self._is_test_path(path) and not self._is_fixture_path(path)
            ]
            if non_test_paths:
                violations.append(
                    GuardrailViolation(
                        rule="tester_scope",
                        message="Tester results may modify tests and fixtures only.",
                    )
                )

        if task.assigned_agent == "reviewer" and changed_files:
            violations.append(
                GuardrailViolation(
                    rule="reviewer_mutation",
                    message="Reviewer may not mutate implementation or tests as part of review.",
                )
            )

        if payload.get("pushed_to_main"):
            violations.append(
                GuardrailViolation(
                    rule="push_to_main",
                    message="No task may push directly to main.",
                )
            )

        return GuardrailDecision(allowed=not violations, violations=tuple(violations))

    def validate_result_source(
        self,
        task: TaskNode,
        event: AgentEvent,
        graph: TaskGraph,
    ) -> GuardrailDecision:
        violations: list[GuardrailViolation] = []
        violations.extend(self._missing_rules_violations())
        payload = event.payload

        if task.assigned_agent != "system":
            if event.source != task.assigned_agent:
                violations.append(
                    GuardrailViolation(
                        rule="result_ownership",
                        message=(
                            f"Task '{task.task_id}' is owned by '{task.assigned_agent}' but result "
                            f"came from '{event.source}'."
                        ),
                    )
                )
            return GuardrailDecision(allowed=not violations, violations=tuple(violations))

        if task.task_type == "human_approval_gate":
            if event.source != "system":
                violations.append(
                    GuardrailViolation(
                        rule="trusted_source",
                        message="human_approval_gate results must come from source 'system'.",
                    )
                )

            approval_source = str(payload.get("approval_source") or "").strip().lower()
            approval_status = str(payload.get("approval_status") or "").strip().lower()
            approval_actor = str(payload.get("approval_actor") or "").strip()

            if approval_source not in {"human", "system"}:
                violations.append(
                    GuardrailViolation(
                        rule="approval_payload",
                        message="human_approval_gate results must declare approval_source as 'human' or 'system'.",
                    )
                )

            if not approval_status:
                violations.append(
                    GuardrailViolation(
                        rule="approval_payload",
                        message="human_approval_gate results must include approval_status.",
                    )
                )

            if approval_source == "human" and not approval_actor:
                violations.append(
                    GuardrailViolation(
                        rule="approval_payload",
                        message="human approvals must include approval_actor.",
                    )
                )

        elif task.task_type == "merge_task":
            if event.source != "system":
                violations.append(
                    GuardrailViolation(
                        rule="trusted_source",
                        message="merge_task results must come from source 'system'.",
                    )
                )
            if graph.metadata.get("human_approval_status") != "approved":
                violations.append(
                    GuardrailViolation(
                        rule="merge_approval_record",
                        message="merge_task may complete only after recorded human approval.",
                    )
                )

        elif task.task_type == "rerun_ci":
            if event.source not in {"ci", "system"}:
                violations.append(
                    GuardrailViolation(
                        rule="trusted_source",
                        message="rerun_ci results may only come from source 'ci' or 'system'.",
                    )
                )
        elif event.source != "system":
            violations.append(
                GuardrailViolation(
                    rule="trusted_source",
                    message=f"System-owned task '{task.task_id}' must be completed by source 'system'.",
                )
            )

        return GuardrailDecision(allowed=not violations, violations=tuple(violations))

    def validate_transition(
        self,
        task: TaskNode,
        *,
        target_status: TaskStatus,
        graph: TaskGraph,
        event: AgentEvent | None = None,
    ) -> GuardrailDecision:
        del graph
        violations: list[GuardrailViolation] = []
        violations.extend(self._missing_rules_violations())

        if task.status == target_status:
            return GuardrailDecision(allowed=not violations, violations=tuple(violations))

        allowed_transitions = ALLOWED_STATUS_TRANSITIONS.get(task.status, ())
        if target_status not in allowed_transitions:
            violations.append(
                GuardrailViolation(
                    rule="invalid_transition",
                    message=(
                        f"Task '{task.task_id}' may not transition from '{task.status}' "
                        f"to '{target_status}'."
                    ),
                )
            )

        if event is not None:
            if event.event_type == "task_started" and target_status != "running":
                violations.append(
                    GuardrailViolation(
                        rule="task_started_transition",
                        message="task_started events must transition tasks to running.",
                    )
                )
            if event.event_type in {"task_completed", "code_generated"} and target_status != "completed":
                violations.append(
                    GuardrailViolation(
                        rule="task_completed_transition",
                        message=f"{event.event_type} events must transition tasks to completed.",
                    )
                )
            if event.event_type == "task_failed" and target_status != "failed":
                violations.append(
                    GuardrailViolation(
                        rule="task_failed_transition",
                        message="task_failed events must transition tasks to failed.",
                    )
                )

        return GuardrailDecision(allowed=not violations, violations=tuple(violations))

    def validate_memory_payload(self, payload: dict[str, Any]) -> GuardrailDecision:
        violations: list[GuardrailViolation] = []
        violations.extend(self._missing_rules_violations())

        for field_name in RAW_MEMORY_FIELDS:
            if field_name not in payload:
                continue

            value = payload[field_name]
            if value not in (None, "", [], {}, False):
                violations.append(
                    GuardrailViolation(
                        rule="raw_conversation_storage",
                        message=(
                            f"Memory payloads may not include raw conversation field '{field_name}'."
                        ),
                    )
                )

        records = payload.get("records", [])
        if records is None:
            records = []
        if not isinstance(records, list):
            violations.append(
                GuardrailViolation(
                    rule="memory_records_shape",
                    message="Memory payloads must provide records as a list of structured MemoryRecord items.",
                )
            )
            return GuardrailDecision(allowed=not violations, violations=tuple(violations))

        for index, record in enumerate(records):
            if not isinstance(record, dict):
                violations.append(
                    GuardrailViolation(
                        rule="memory_records_shape",
                        message=f"Memory record at index {index} must be an object.",
                    )
                )
                continue

            missing_fields = {"memory_type", "topic", "summary", "confidence", "tags"} - set(record)
            if missing_fields:
                violations.append(
                    GuardrailViolation(
                        rule="memory_records_shape",
                        message=(
                            f"Memory record at index {index} is missing required fields: "
                            f"{', '.join(sorted(missing_fields))}."
                        ),
                    )
                )
                continue

            if record.get("memory_type") not in {"learning", "decision", "architecture", "bug", "improvement"}:
                violations.append(
                    GuardrailViolation(
                        rule="memory_records_shape",
                        message=f"Memory record at index {index} has unsupported memory_type.",
                    )
                )

            if not isinstance(record.get("topic"), str) or not str(record.get("topic")).strip():
                violations.append(
                    GuardrailViolation(
                        rule="memory_records_shape",
                        message=f"Memory record at index {index} must include a non-empty topic.",
                    )
                )

            if not isinstance(record.get("summary"), str) or not str(record.get("summary")).strip():
                violations.append(
                    GuardrailViolation(
                        rule="memory_records_shape",
                        message=f"Memory record at index {index} must include a non-empty summary.",
                    )
                )

            confidence = record.get("confidence")
            if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
                violations.append(
                    GuardrailViolation(
                        rule="memory_records_shape",
                        message=f"Memory record at index {index} must include confidence between 0.0 and 1.0.",
                    )
                )

            tags = record.get("tags")
            if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
                violations.append(
                    GuardrailViolation(
                        rule="memory_records_shape",
                        message=f"Memory record at index {index} must include tags as non-empty strings.",
                    )
                )

        return GuardrailDecision(allowed=not violations, violations=tuple(violations))

    def dry_run_validation(self) -> dict[str, Any]:
        return {
            "rules_root": str(self.rules_root),
            "loaded_rules": sorted(self.load_rule_text().keys()),
            "missing_rules": self.missing_rule_files(),
            "sample_memory_payload_allowed": self.validate_memory_payload({"records": []}).allowed,
        }

    @staticmethod
    def _ownership_violation(task: TaskNode, *, expected: str) -> GuardrailViolation:
        return GuardrailViolation(
            rule="task_ownership",
            message=f"Task '{task.task_id}' must be assigned to '{expected}'.",
        )

    @staticmethod
    def _is_test_path(path: str) -> bool:
        normalized = path.replace("\\", "/").lower()
        return (
            normalized.startswith("tests/")
            or normalized.startswith("fixtures/")
            or "/tests/" in normalized
            or "/fixtures/" in normalized
            or normalized.endswith("_test.py")
            or normalized.endswith("test.py")
        )

    @staticmethod
    def _is_ci_path(path: str) -> bool:
        normalized = path.replace("\\", "/").lower()
        return normalized.startswith(".github/") or "/ci/" in normalized or normalized.startswith("ci/")

    @staticmethod
    def _is_fixture_path(path: str) -> bool:
        normalized = path.replace("\\", "/").lower()
        return normalized.startswith("fixtures/") or "/fixtures/" in normalized

    def _missing_rules_violations(self) -> list[GuardrailViolation]:
        return [
            GuardrailViolation(
                rule="missing_rule_file",
                message=f"Required guardrail file '{rule_name}' is missing from '{self.rules_root}'.",
            )
            for rule_name in self.missing_rule_files()
        ]
