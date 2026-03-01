"""Tests for cue.core.models — shared data types."""

from __future__ import annotations

from cue.core.models import (
    ActionContext,
    ActionRecord,
    PolicyAction,
    PolicyDecision,
    RiskLevel,
    SessionStatus,
)


class TestRiskLevel:
    def test_ordering(self):
        assert RiskLevel.LOW < RiskLevel.MEDIUM < RiskLevel.HIGH < RiskLevel.CRITICAL

    def test_integer_values(self):
        assert int(RiskLevel.LOW) == 1
        assert int(RiskLevel.CRITICAL) == 4

    def test_comparison_with_int(self):
        assert RiskLevel.MEDIUM >= 2
        assert RiskLevel.HIGH > 2


class TestPolicyAction:
    def test_values(self):
        assert PolicyAction.ALLOW.value == "allow"
        assert PolicyAction.DENY.value == "deny"
        assert PolicyAction.WARN.value == "warn"


class TestPolicyDecision:
    def test_frozen(self):
        decision = PolicyDecision(action=PolicyAction.ALLOW)
        try:
            decision.action = PolicyAction.DENY  # type: ignore[misc]
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass

    def test_defaults(self):
        decision = PolicyDecision(action=PolicyAction.DENY)
        assert decision.rule_name == ""
        assert decision.reason == ""
        assert decision.risk_level == RiskLevel.LOW


class TestActionContext:
    def test_frozen(self):
        ctx = ActionContext(tool="cue_click")
        try:
            ctx.tool = "cue_type"  # type: ignore[misc]
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass

    def test_defaults(self):
        ctx = ActionContext(tool="cue_screenshot")
        assert ctx.params == {}
        assert ctx.target_app is None
        assert ctx.key_combo is None

    def test_with_all_fields(self):
        ctx = ActionContext(
            tool="cue_key",
            params={"keys": "ctrl+c"},
            target_app="Notepad",
            key_combo="ctrl+c",
        )
        assert ctx.tool == "cue_key"
        assert ctx.key_combo == "ctrl+c"


class TestSessionStatus:
    def test_values(self):
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.PAUSED.value == "paused"
        assert SessionStatus.TERMINATED.value == "terminated"


class TestActionRecord:
    def test_auto_id(self):
        r1 = ActionRecord()
        r2 = ActionRecord()
        assert r1.id != r2.id
        assert len(r1.id) == 12

    def test_defaults(self):
        r = ActionRecord()
        assert r.tool == ""
        assert r.risk_level == RiskLevel.LOW
        assert r.decision == PolicyAction.ALLOW
        assert r.result is None
        assert r.error is None
        assert r.duration_ms is None
