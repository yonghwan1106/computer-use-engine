"""CUE safety pipeline — integrates policy, session, and event streaming."""

from __future__ import annotations

from typing import Any, Optional

from cue.core.models import ActionContext, PolicyAction, PolicyDecision, RiskLevel
from cue.monitor.events import Event, EventBus, EventType


class SafetyPipeline:
    """Central integration layer connecting policy engine, session manager,
    event bus, and audit logger into the tool execution flow."""

    def __init__(
        self,
        policy_engine: Any,
        session_manager: Any,
        event_bus: EventBus,
        audit: Any,
    ) -> None:
        self.policy_engine = policy_engine
        self.session_manager = session_manager
        self.event_bus = event_bus
        self.audit = audit

    def pre_action(
        self,
        tool: str,
        params: Optional[dict[str, Any]] = None,
        target_app: Optional[str] = None,
        key_combo: Optional[str] = None,
    ) -> PolicyDecision:
        """Evaluate policy before action execution.

        Emits POLICY_DECISION and ACTION_STARTED events.
        Raises PermissionError if the policy denies the action.
        Emits RISK_ALERT for WARN decisions.
        """
        context = ActionContext(
            tool=tool,
            params=params or {},
            target_app=target_app,
            key_combo=key_combo,
        )
        decision = self.policy_engine.evaluate(context)

        # Emit policy decision event
        self.event_bus.emit(Event(
            type=EventType.POLICY_DECISION,
            data={
                "tool": tool,
                "action": decision.action.value,
                "rule_name": decision.rule_name,
                "reason": decision.reason,
                "risk_level": decision.risk_level.name,
            },
        ))

        if decision.action == PolicyAction.DENY:
            self.event_bus.emit(Event(
                type=EventType.ACTION_DENIED,
                data={
                    "tool": tool,
                    "params": params or {},
                    "rule_name": decision.rule_name,
                    "reason": decision.reason,
                },
            ))
            raise PermissionError(
                f"Action denied by policy '{decision.rule_name}': {decision.reason}"
            )

        if decision.action == PolicyAction.WARN:
            self.event_bus.emit(Event(
                type=EventType.RISK_ALERT,
                data={
                    "tool": tool,
                    "risk_level": decision.risk_level.name,
                    "rule_name": decision.rule_name,
                    "reason": decision.reason,
                },
            ))

        # Emit action started
        self.event_bus.emit(Event(
            type=EventType.ACTION_STARTED,
            data={
                "tool": tool,
                "params": params or {},
                "risk_level": decision.risk_level.name,
            },
        ))

        return decision

    def post_action(
        self,
        tool: str,
        params: Optional[dict[str, Any]] = None,
        result: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
        decision: Optional[PolicyDecision] = None,
    ) -> None:
        """Record action completion and emit events.

        Delegates to SessionManager for history tracking and AuditLogger
        for compliance logging.
        """
        risk_level = decision.risk_level if decision else RiskLevel.LOW
        policy_action = decision.action if decision else PolicyAction.ALLOW

        # Record in session
        self.session_manager.record_action(
            tool=tool,
            params=params,
            risk_level=risk_level,
            decision=policy_action,
            result=result,
            error=error,
            duration_ms=duration_ms,
        )

        # Emit completion event
        self.event_bus.emit(Event(
            type=EventType.ACTION_COMPLETED,
            data={
                "tool": tool,
                "params": params or {},
                "result": result,
                "error": error,
                "duration_ms": duration_ms,
                "risk_level": risk_level.name,
            },
        ))

        # Delegate to audit logger
        self.audit.log(
            tool=tool,
            params=params or {},
            result=result,
            error=error,
            duration_ms=duration_ms,
        )
