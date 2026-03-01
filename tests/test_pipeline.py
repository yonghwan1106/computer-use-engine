"""Tests for SafetyPipeline — policy evaluation, event emission, and session recording."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from cue.core.approval import ApprovalManager
from cue.core.models import (
    ActionContext,
    ApprovalRequiredError,
    PolicyAction,
    PolicyDecision,
    RiskLevel,
)
from cue.monitor.events import EventBus, EventType
from cue.safety.pipeline import SafetyPipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def mock_policy_engine():
    engine = MagicMock()
    engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.ALLOW,
        rule_name="default",
        reason="allowed",
        risk_level=RiskLevel.LOW,
    )
    return engine


@pytest.fixture
def mock_session_manager():
    return MagicMock()


@pytest.fixture
def mock_audit():
    return MagicMock()


@pytest.fixture
def pipeline(mock_policy_engine, mock_session_manager, event_bus, mock_audit):
    return SafetyPipeline(mock_policy_engine, mock_session_manager, event_bus, mock_audit)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _types(event_bus: EventBus) -> list[EventType]:
    return [e.type for e in event_bus.get_buffered()]


# ---------------------------------------------------------------------------
# pre_action tests
# ---------------------------------------------------------------------------

def test_pre_action_returns_policy_decision_on_allow(pipeline):
    """pre_action returns the PolicyDecision produced by the policy engine."""
    decision = pipeline.pre_action("click", params={"x": 10, "y": 20})

    assert isinstance(decision, PolicyDecision)
    assert decision.action == PolicyAction.ALLOW
    assert decision.rule_name == "default"


def test_pre_action_emits_policy_decision_event(pipeline, event_bus):
    """pre_action always emits a POLICY_DECISION event."""
    pipeline.pre_action("click")

    policy_events = event_bus.get_buffered(event_type=EventType.POLICY_DECISION)
    assert len(policy_events) == 1
    data = policy_events[0].data
    assert data["tool"] == "click"
    assert data["action"] == PolicyAction.ALLOW.value
    assert data["rule_name"] == "default"
    assert data["reason"] == "allowed"
    assert data["risk_level"] == RiskLevel.LOW.name


def test_pre_action_emits_action_started_on_allow(pipeline, event_bus):
    """ALLOW decision causes an ACTION_STARTED event to be emitted."""
    pipeline.pre_action("type_text", params={"text": "hello"})

    started_events = event_bus.get_buffered(event_type=EventType.ACTION_STARTED)
    assert len(started_events) == 1
    assert started_events[0].data["tool"] == "type_text"


def test_pre_action_raises_permission_error_on_deny(pipeline, mock_policy_engine):
    """DENY decision raises PermissionError containing rule_name and reason."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.DENY,
        rule_name="block_registry",
        reason="registry access blocked",
        risk_level=RiskLevel.CRITICAL,
    )

    with pytest.raises(PermissionError) as exc_info:
        pipeline.pre_action("registry_write")

    assert "block_registry" in str(exc_info.value)
    assert "registry access blocked" in str(exc_info.value)


def test_pre_action_emits_action_denied_event_on_deny(pipeline, mock_policy_engine, event_bus):
    """DENY decision emits an ACTION_DENIED event with correct payload."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.DENY,
        rule_name="block_registry",
        reason="registry access blocked",
        risk_level=RiskLevel.CRITICAL,
    )

    with pytest.raises(PermissionError):
        pipeline.pre_action("registry_write", params={"key": "HKLM"})

    denied_events = event_bus.get_buffered(event_type=EventType.ACTION_DENIED)
    assert len(denied_events) == 1
    data = denied_events[0].data
    assert data["tool"] == "registry_write"
    assert data["rule_name"] == "block_registry"
    assert data["reason"] == "registry access blocked"


def test_pre_action_does_not_emit_action_started_on_deny(pipeline, mock_policy_engine, event_bus):
    """DENY decision must NOT emit ACTION_STARTED."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.DENY,
        rule_name="block_all",
        reason="denied",
        risk_level=RiskLevel.HIGH,
    )

    with pytest.raises(PermissionError):
        pipeline.pre_action("screenshot")

    started_events = event_bus.get_buffered(event_type=EventType.ACTION_STARTED)
    assert len(started_events) == 0


def test_pre_action_emits_risk_alert_on_warn(pipeline, mock_policy_engine, event_bus):
    """WARN decision emits a RISK_ALERT event."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.WARN,
        rule_name="sensitive_key",
        reason="potentially dangerous key combo",
        risk_level=RiskLevel.HIGH,
    )

    pipeline.pre_action("hotkey", key_combo="ctrl+alt+del")

    risk_events = event_bus.get_buffered(event_type=EventType.RISK_ALERT)
    assert len(risk_events) == 1
    data = risk_events[0].data
    assert data["tool"] == "hotkey"
    assert data["risk_level"] == RiskLevel.HIGH.name
    assert data["rule_name"] == "sensitive_key"


def test_pre_action_emits_action_started_on_warn(pipeline, mock_policy_engine, event_bus):
    """WARN decision still proceeds: ACTION_STARTED must be emitted."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.WARN,
        rule_name="sensitive_key",
        reason="potentially dangerous key combo",
        risk_level=RiskLevel.MEDIUM,
    )

    pipeline.pre_action("hotkey", key_combo="ctrl+shift+esc")

    started_events = event_bus.get_buffered(event_type=EventType.ACTION_STARTED)
    assert len(started_events) == 1
    assert started_events[0].data["tool"] == "hotkey"


# ---------------------------------------------------------------------------
# post_action tests
# ---------------------------------------------------------------------------

def test_post_action_calls_session_manager_record_action(pipeline, mock_session_manager):
    """post_action delegates to session_manager.record_action with correct args."""
    decision = PolicyDecision(
        action=PolicyAction.ALLOW,
        rule_name="default",
        reason="allowed",
        risk_level=RiskLevel.LOW,
    )

    pipeline.post_action(
        tool="click",
        params={"x": 5, "y": 10},
        result="ok",
        error=None,
        duration_ms=42.0,
        decision=decision,
    )

    mock_session_manager.record_action.assert_called_once_with(
        tool="click",
        params={"x": 5, "y": 10},
        risk_level=RiskLevel.LOW,
        decision=PolicyAction.ALLOW,
        result="ok",
        error=None,
        duration_ms=42.0,
    )


def test_post_action_emits_action_completed_event(pipeline, event_bus):
    """post_action emits an ACTION_COMPLETED event with correct payload."""
    decision = PolicyDecision(
        action=PolicyAction.ALLOW,
        rule_name="default",
        reason="allowed",
        risk_level=RiskLevel.LOW,
    )

    pipeline.post_action(
        tool="screenshot",
        params={},
        result="captured",
        duration_ms=100.0,
        decision=decision,
    )

    completed_events = event_bus.get_buffered(event_type=EventType.ACTION_COMPLETED)
    assert len(completed_events) == 1
    data = completed_events[0].data
    assert data["tool"] == "screenshot"
    assert data["result"] == "captured"
    assert data["risk_level"] == RiskLevel.LOW.name
    assert data["duration_ms"] == 100.0


def test_post_action_calls_audit_log(pipeline, mock_audit):
    """post_action delegates to audit.log with correct keyword arguments."""
    pipeline.post_action(
        tool="type_text",
        params={"text": "hello"},
        result="typed",
        error=None,
        duration_ms=25.0,
    )

    mock_audit.log.assert_called_once_with(
        tool="type_text",
        params={"text": "hello"},
        result="typed",
        error=None,
        duration_ms=25.0,
    )


def test_post_action_with_error_parameter(pipeline, event_bus, mock_audit):
    """post_action propagates error into the ACTION_COMPLETED event and audit log."""
    pipeline.post_action(
        tool="click",
        params={"x": 0, "y": 0},
        result=None,
        error="target not found",
        duration_ms=5.0,
    )

    completed_events = event_bus.get_buffered(event_type=EventType.ACTION_COMPLETED)
    assert completed_events[0].data["error"] == "target not found"
    assert completed_events[0].data["result"] is None

    _, kwargs = mock_audit.log.call_args
    assert kwargs["error"] == "target not found"


def test_post_action_no_decision_defaults_to_low_risk(pipeline, mock_session_manager, event_bus):
    """When decision is None, post_action defaults risk_level to LOW."""
    pipeline.post_action(tool="screenshot", params={}, result="ok", decision=None)

    _, kwargs = mock_session_manager.record_action.call_args
    assert kwargs["risk_level"] == RiskLevel.LOW
    assert kwargs["decision"] == PolicyAction.ALLOW

    completed_events = event_bus.get_buffered(event_type=EventType.ACTION_COMPLETED)
    assert completed_events[0].data["risk_level"] == RiskLevel.LOW.name


# ---------------------------------------------------------------------------
# Context construction test
# ---------------------------------------------------------------------------

def test_pre_action_passes_correct_action_context_to_policy_engine(
    pipeline, mock_policy_engine
):
    """pre_action builds ActionContext with all provided fields and passes it to evaluate."""
    pipeline.pre_action(
        tool="hotkey",
        params={"modifier": "ctrl"},
        target_app="notepad",
        key_combo="ctrl+s",
    )

    mock_policy_engine.evaluate.assert_called_once()
    ctx: ActionContext = mock_policy_engine.evaluate.call_args[0][0]
    assert isinstance(ctx, ActionContext)
    assert ctx.tool == "hotkey"
    assert ctx.params == {"modifier": "ctrl"}
    assert ctx.target_app == "notepad"
    assert ctx.key_combo == "ctrl+s"


# ---------------------------------------------------------------------------
# Full flow test
# ---------------------------------------------------------------------------

def test_full_flow_pre_and_post_action_event_sequence(
    pipeline, mock_policy_engine, event_bus
):
    """Full pre_action + post_action cycle produces events in the expected order."""
    decision = pipeline.pre_action("click", params={"x": 100, "y": 200})
    pipeline.post_action(
        tool="click",
        params={"x": 100, "y": 200},
        result="clicked",
        duration_ms=30.0,
        decision=decision,
    )

    types = _types(event_bus)
    assert types == [
        EventType.POLICY_DECISION,
        EventType.ACTION_STARTED,
        EventType.ACTION_COMPLETED,
    ]

    # Verify cross-event consistency
    all_events = event_bus.get_buffered()
    policy_data = all_events[0].data
    started_data = all_events[1].data
    completed_data = all_events[2].data

    assert policy_data["tool"] == "click"
    assert started_data["tool"] == "click"
    assert completed_data["tool"] == "click"
    assert completed_data["result"] == "clicked"
    assert completed_data["risk_level"] == RiskLevel.LOW.name


# ---------------------------------------------------------------------------
# HOLD policy tests (Phase 3)
# ---------------------------------------------------------------------------

@pytest.fixture
def approval_manager():
    return ApprovalManager(timeout=300.0, grant_ttl=60.0)


@pytest.fixture
def hold_pipeline(mock_policy_engine, mock_session_manager, event_bus, mock_audit, approval_manager):
    return SafetyPipeline(
        mock_policy_engine, mock_session_manager, event_bus, mock_audit,
        approval_manager=approval_manager,
    )


def test_hold_raises_approval_required_error(hold_pipeline, mock_policy_engine):
    """HOLD decision raises ApprovalRequiredError with request_id."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.HOLD,
        rule_name="hold_dangerous",
        reason="Dangerous action needs approval",
        risk_level=RiskLevel.HIGH,
    )

    with pytest.raises(ApprovalRequiredError) as exc_info:
        hold_pipeline.pre_action("cue_click", params={"x": 500})

    err = exc_info.value
    assert err.tool == "cue_click"
    assert err.reason == "Dangerous action needs approval"
    assert isinstance(err.request_id, str)
    assert len(err.request_id) == 12


def test_hold_is_caught_by_permission_error(hold_pipeline, mock_policy_engine):
    """ApprovalRequiredError is a PermissionError subclass — existing catch blocks work."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.HOLD,
        rule_name="hold_all",
        reason="test",
        risk_level=RiskLevel.MEDIUM,
    )

    with pytest.raises(PermissionError):
        hold_pipeline.pre_action("cue_click")


def test_hold_emits_approval_required_event(hold_pipeline, mock_policy_engine, event_bus):
    """HOLD emits APPROVAL_REQUIRED event with request details."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.HOLD,
        rule_name="hold_clicks",
        reason="needs review",
        risk_level=RiskLevel.HIGH,
    )

    with pytest.raises(ApprovalRequiredError):
        hold_pipeline.pre_action("cue_click", params={"x": 10})

    events = event_bus.get_buffered(event_type=EventType.APPROVAL_REQUIRED)
    assert len(events) == 1
    data = events[0].data
    assert data["tool"] == "cue_click"
    assert data["reason"] == "needs review"
    assert data["rule_name"] == "hold_clicks"
    assert "request_id" in data


def test_hold_does_not_emit_action_started(hold_pipeline, mock_policy_engine, event_bus):
    """HOLD must NOT emit ACTION_STARTED."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.HOLD,
        rule_name="hold_all",
        reason="test",
        risk_level=RiskLevel.HIGH,
    )

    with pytest.raises(ApprovalRequiredError):
        hold_pipeline.pre_action("cue_click")

    started = event_bus.get_buffered(event_type=EventType.ACTION_STARTED)
    assert len(started) == 0


def test_hold_without_approval_manager_falls_back_to_deny(
    mock_policy_engine, mock_session_manager, event_bus, mock_audit
):
    """HOLD with no approval_manager raises PermissionError (DENY fallback)."""
    pipe = SafetyPipeline(mock_policy_engine, mock_session_manager, event_bus, mock_audit)
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.HOLD,
        rule_name="hold_rule",
        reason="test",
        risk_level=RiskLevel.HIGH,
    )

    with pytest.raises(PermissionError, match="HOLD fallback"):
        pipe.pre_action("cue_click")

    # Should emit ACTION_DENIED, not APPROVAL_REQUIRED
    denied = event_bus.get_buffered(event_type=EventType.ACTION_DENIED)
    assert len(denied) == 1
    approval = event_bus.get_buffered(event_type=EventType.APPROVAL_REQUIRED)
    assert len(approval) == 0


def test_grant_bypasses_policy(hold_pipeline, mock_policy_engine, approval_manager, event_bus):
    """After approval, the grant lets the action bypass policy evaluation."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.HOLD,
        rule_name="hold_clicks",
        reason="risky",
        risk_level=RiskLevel.HIGH,
    )

    # First call: HOLD → ApprovalRequiredError
    with pytest.raises(ApprovalRequiredError) as exc_info:
        hold_pipeline.pre_action("cue_click", params={"x": 500})

    request_id = exc_info.value.request_id

    # Approve the request
    approval_manager.approve(request_id)

    # Second call: grant consumed → ALLOW without policy evaluation
    decision = hold_pipeline.pre_action("cue_click", params={"x": 500})
    assert decision.action == PolicyAction.ALLOW
    assert decision.rule_name == "approval_grant"

    # ACTION_STARTED should be emitted with grant info
    started = event_bus.get_buffered(event_type=EventType.ACTION_STARTED)
    assert any(e.data.get("grant_used") == request_id for e in started)


def test_grant_is_one_time_use(hold_pipeline, mock_policy_engine, approval_manager):
    """A consumed grant cannot be reused."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.HOLD,
        rule_name="hold_clicks",
        reason="risky",
        risk_level=RiskLevel.HIGH,
    )

    # Create request and approve
    with pytest.raises(ApprovalRequiredError) as exc_info:
        hold_pipeline.pre_action("cue_click")
    approval_manager.approve(exc_info.value.request_id)

    # First retry: succeeds
    hold_pipeline.pre_action("cue_click")

    # Second retry: HOLD again (grant consumed)
    with pytest.raises(ApprovalRequiredError):
        hold_pipeline.pre_action("cue_click")


def test_full_hold_approve_retry_flow(
    hold_pipeline, mock_policy_engine, approval_manager, event_bus, mock_session_manager
):
    """End-to-end: HOLD → approve → retry → post_action."""
    mock_policy_engine.evaluate.return_value = PolicyDecision(
        action=PolicyAction.HOLD,
        rule_name="hold_clicks",
        reason="risky click",
        risk_level=RiskLevel.HIGH,
    )

    # Step 1: HOLD
    with pytest.raises(ApprovalRequiredError) as exc_info:
        hold_pipeline.pre_action("cue_click", params={"x": 100, "y": 200})

    # Step 2: Approve
    approval_manager.approve(exc_info.value.request_id)

    # Step 3: Retry → succeeds
    decision = hold_pipeline.pre_action("cue_click", params={"x": 100, "y": 200})
    assert decision.action == PolicyAction.ALLOW

    # Step 4: Post action
    hold_pipeline.post_action(
        tool="cue_click",
        params={"x": 100, "y": 200},
        result="clicked",
        decision=decision,
    )

    # Verify events: POLICY_DECISION, APPROVAL_REQUIRED, ACTION_STARTED, ACTION_COMPLETED
    types = _types(event_bus)
    assert EventType.POLICY_DECISION in types
    assert EventType.APPROVAL_REQUIRED in types
    assert EventType.ACTION_STARTED in types
    assert EventType.ACTION_COMPLETED in types
