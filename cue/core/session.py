"""CUE session management — track agent sessions and action history."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from cue.core.models import (
    ActionRecord,
    PolicyAction,
    RiskLevel,
    SessionStatus,
)
from cue.monitor.events import EventType


class Session:
    """A single agent session that tracks actions and state."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        max_actions: int = 0,
    ) -> None:
        self.id = session_id or uuid.uuid4().hex[:16]
        self.max_actions = max_actions
        self.status = SessionStatus.ACTIVE
        self.created_at = datetime.now(timezone.utc)
        self._history: list[ActionRecord] = []

    @property
    def action_count(self) -> int:
        return len(self._history)

    @property
    def history(self) -> list[ActionRecord]:
        return list(self._history)

    def record_action(
        self,
        tool: str,
        params: Optional[dict[str, Any]] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        decision: PolicyAction = PolicyAction.ALLOW,
        result: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> ActionRecord:
        """Record an action and return the created record.

        Raises RuntimeError if the session limit is exceeded or the session
        is not active.
        """
        if self.status != SessionStatus.ACTIVE:
            raise RuntimeError(
                f"Cannot record action: session is {self.status.value}."
            )

        if self.max_actions > 0 and self.action_count >= self.max_actions:
            raise RuntimeError(
                f"Session action limit reached ({self.max_actions}). "
                "Reset the session or increase the limit in config."
            )

        record = ActionRecord(
            tool=tool,
            params=params or {},
            risk_level=risk_level,
            decision=decision,
            result=result,
            error=error,
            duration_ms=duration_ms,
        )
        self._history.append(record)
        return record

    def pause(self) -> None:
        """Pause the session. No actions can be recorded while paused."""
        if self.status != SessionStatus.ACTIVE:
            raise RuntimeError(
                f"Cannot pause: session is {self.status.value}."
            )
        self.status = SessionStatus.PAUSED

    def resume(self) -> None:
        """Resume a paused session."""
        if self.status != SessionStatus.PAUSED:
            raise RuntimeError(
                f"Cannot resume: session is {self.status.value}."
            )
        self.status = SessionStatus.ACTIVE

    def terminate(self) -> None:
        """Terminate the session permanently."""
        if self.status == SessionStatus.TERMINATED:
            return  # idempotent
        self.status = SessionStatus.TERMINATED

    def summary(self) -> dict[str, Any]:
        """Return a summary of this session."""
        risk_breakdown: dict[str, int] = {level.name: 0 for level in RiskLevel}
        error_count = 0

        for record in self._history:
            risk_breakdown[record.risk_level.name] += 1
            if record.error is not None:
                error_count += 1

        return {
            "session_id": self.id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "action_count": self.action_count,
            "risk_breakdown": risk_breakdown,
            "error_count": error_count,
        }


class SessionManager:
    """Manage session lifecycle and delegate action recording."""

    def __init__(self, max_actions: int = 0) -> None:
        self.max_actions = max_actions
        self._current: Optional[Session] = None
        self._sessions: list[Session] = []
        self.event_bus = None

    @property
    def current_session(self) -> Optional[Session]:
        return self._current

    @property
    def action_count(self) -> int:
        """Action count of the current session, or 0 if none."""
        if self._current is not None:
            return self._current.action_count
        return 0

    def _emit(self, event_type: EventType, data: dict) -> None:
        """Emit an event if event_bus is available."""
        if self.event_bus is not None:
            from cue.monitor.events import Event
            self.event_bus.emit(Event(type=event_type, data=data))

    def start_session(self) -> Session:
        """Start a new session, terminating the current one if any."""
        if self._current is not None and self._current.status != SessionStatus.TERMINATED:
            self._current.terminate()
        session = Session(max_actions=self.max_actions)
        self._current = session
        self._sessions.append(session)
        self._emit(EventType.SESSION_STARTED, {"session_id": session.id, "max_actions": self.max_actions})
        return session

    def ensure_session(self) -> Session:
        """Return the current active session or start a new one."""
        if self._current is not None and self._current.status == SessionStatus.ACTIVE:
            return self._current
        return self.start_session()

    def record_action(
        self,
        tool: str,
        params: Optional[dict[str, Any]] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        decision: PolicyAction = PolicyAction.ALLOW,
        result: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> ActionRecord:
        """Record an action in the current session (auto-started if needed)."""
        session = self.ensure_session()
        return session.record_action(
            tool=tool,
            params=params,
            risk_level=risk_level,
            decision=decision,
            result=result,
            error=error,
            duration_ms=duration_ms,
        )

    def reset(self) -> None:
        """Terminate current session and start fresh."""
        if self._current is not None:
            self._current.terminate()
            self._emit(EventType.SESSION_TERMINATED, {"session_id": self._current.id})
        self._current = None

    def get_history(self) -> list[dict[str, Any]]:
        """Return serializable history of all sessions."""
        return [s.summary() for s in self._sessions]
