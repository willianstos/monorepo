"""Phase 1 scheduler contracts for the AI coding assistant workspace."""

from .ci_handler import CIEventHandler
from .dag_builder import DagBuilder, TaskGraph, TaskNode, TaskStatus
from .dag_store import RedisDagStore
from .dispatcher import TaskDispatcher
from .guardrail_enforcer import GuardrailDecision, GuardrailEnforcer, GuardrailViolation
from .service import SchedulerService

TaskGraphScheduler = SchedulerService

__all__ = [
    "CIEventHandler",
    "DagBuilder",
    "GuardrailDecision",
    "GuardrailEnforcer",
    "GuardrailViolation",
    "RedisDagStore",
    "SchedulerService",
    "TaskDispatcher",
    "TaskGraphScheduler",
    "TaskGraph",
    "TaskNode",
    "TaskStatus",
]
