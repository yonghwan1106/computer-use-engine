"""CUE core data models — shared types for policy, risk, and session."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any, Optional


class RiskLevel(IntEnum):
    """Risk tier for an action. Higher value = higher risk."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class PolicyAction(Enum):
    """Decision an engine can make about an action."""

    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    HOLD = "hold"


class ApprovalRequiredError(PermissionError):
    """HOLD policy decision — requires human approval before proceeding.

    Inherits PermissionError so existing tool catch blocks handle it naturally.
    """

    def __init__(self, request_id: str, tool: str, reason: str) -> None:
        self.request_id = request_id
        self.tool = tool
        self.reason = reason
        super().__init__(
            f"Action requires approval [ID: {request_id}]. "
            f"Reason: {reason}. "
            f"Ask the user to approve, then call cue_approve_action('{request_id}')."
        )


@dataclass(frozen=True)
class PolicyDecision:
    """Immutable result of a policy evaluation."""

    action: PolicyAction
    rule_name: str = ""
    reason: str = ""
    risk_level: RiskLevel = RiskLevel.LOW


@dataclass(frozen=True)
class ActionContext:
    """Immutable description of an action to be evaluated."""

    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    target_app: Optional[str] = None
    key_combo: Optional[str] = None


class SessionStatus(Enum):
    """Lifecycle state of a session."""

    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


@dataclass
class ActionRecord:
    """Single recorded action within a session."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tool: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    decision: PolicyAction = PolicyAction.ALLOW
    result: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
