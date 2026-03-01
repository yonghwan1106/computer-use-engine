"""Tests for cue.core.policy — rule-based policy engine."""

from __future__ import annotations

import pytest

from cue.core.models import ActionContext, PolicyAction, PolicyDecision, RiskLevel
from cue.core.policy import PolicyEngine, PolicyRule
from cue.core.risk import RiskScorer


@pytest.fixture
def risk_scorer():
    return RiskScorer()


class TestPolicyRule:
    def test_match_by_tool(self):
        rule = PolicyRule("r1", PolicyAction.ALLOW, {"tool": "cue_screenshot"})
        ctx = ActionContext(tool="cue_screenshot")
        assert rule.matches(ctx, RiskLevel.LOW)

    def test_no_match_wrong_tool(self):
        rule = PolicyRule("r1", PolicyAction.ALLOW, {"tool": "cue_screenshot"})
        ctx = ActionContext(tool="cue_click")
        assert not rule.matches(ctx, RiskLevel.MEDIUM)

    def test_match_tool_list(self):
        rule = PolicyRule("r1", PolicyAction.ALLOW, {"tool": ["cue_screenshot", "cue_screen_size"]})
        ctx = ActionContext(tool="cue_screen_size")
        assert rule.matches(ctx, RiskLevel.LOW)

    def test_match_by_target_app(self):
        rule = PolicyRule("r1", PolicyAction.DENY, {"target_app": "Registry Editor"})
        ctx = ActionContext(tool="cue_click", target_app="Registry Editor")
        assert rule.matches(ctx, RiskLevel.MEDIUM)

    def test_target_app_substring(self):
        rule = PolicyRule("r1", PolicyAction.DENY, {"target_app": "Registry Editor"})
        ctx = ActionContext(tool="cue_click", target_app="Registry Editor - HKEY")
        assert rule.matches(ctx, RiskLevel.MEDIUM)

    def test_no_match_missing_target_app(self):
        rule = PolicyRule("r1", PolicyAction.DENY, {"target_app": "Registry Editor"})
        ctx = ActionContext(tool="cue_click")
        assert not rule.matches(ctx, RiskLevel.MEDIUM)

    def test_match_by_key_combo(self):
        rule = PolicyRule("r1", PolicyAction.DENY, {"key_combo": "win+r"})
        ctx = ActionContext(tool="cue_key", key_combo="win+r")
        assert rule.matches(ctx, RiskLevel.CRITICAL)

    def test_key_combo_order_independent(self):
        rule = PolicyRule("r1", PolicyAction.DENY, {"key_combo": "ctrl+alt+del"})
        ctx = ActionContext(tool="cue_key", key_combo="del+ctrl+alt")
        assert rule.matches(ctx, RiskLevel.CRITICAL)

    def test_match_by_risk_level_threshold(self):
        rule = PolicyRule("r1", PolicyAction.WARN, {"risk_level": "HIGH"})
        ctx = ActionContext(tool="cue_key")
        assert rule.matches(ctx, RiskLevel.HIGH)
        assert rule.matches(ctx, RiskLevel.CRITICAL)
        assert not rule.matches(ctx, RiskLevel.MEDIUM)

    def test_combined_conditions(self):
        rule = PolicyRule("r1", PolicyAction.DENY, {
            "tool": "cue_key",
            "risk_level": "CRITICAL",
        })
        ctx = ActionContext(tool="cue_key", key_combo="win+r")
        assert rule.matches(ctx, RiskLevel.CRITICAL)

    def test_combined_conditions_partial_no_match(self):
        rule = PolicyRule("r1", PolicyAction.DENY, {
            "tool": "cue_key",
            "risk_level": "CRITICAL",
        })
        ctx = ActionContext(tool="cue_click")
        assert not rule.matches(ctx, RiskLevel.CRITICAL)


class TestPolicyEngine:
    def test_first_match_wins(self, risk_scorer):
        rules = [
            PolicyRule("allow_screenshot", PolicyAction.ALLOW, {"tool": "cue_screenshot"}),
            PolicyRule("deny_all", PolicyAction.DENY, {"risk_level": "LOW"}),
        ]
        engine = PolicyEngine(rules, PolicyAction.DENY, risk_scorer)
        ctx = ActionContext(tool="cue_screenshot")
        decision = engine.evaluate(ctx)
        assert decision.action == PolicyAction.ALLOW
        assert decision.rule_name == "allow_screenshot"

    def test_default_action_when_no_match(self, risk_scorer):
        engine = PolicyEngine([], PolicyAction.ALLOW, risk_scorer)
        ctx = ActionContext(tool="cue_click")
        decision = engine.evaluate(ctx)
        assert decision.action == PolicyAction.ALLOW
        assert decision.rule_name == "default"

    def test_risk_level_included_in_decision(self, risk_scorer):
        engine = PolicyEngine([], PolicyAction.ALLOW, risk_scorer)
        ctx = ActionContext(tool="cue_key", key_combo="win+r")
        decision = engine.evaluate(ctx)
        assert decision.risk_level == RiskLevel.CRITICAL

    def test_from_config_basic(self, risk_scorer):
        policy_data = {
            "enabled": True,
            "default_action": "allow",
            "rules": [
                {
                    "name": "block_critical",
                    "conditions": {"risk_level": "CRITICAL"},
                    "action": "deny",
                },
            ],
        }
        engine = PolicyEngine.from_config(policy_data, risk_scorer)
        ctx = ActionContext(tool="cue_key", key_combo="win+r")
        decision = engine.evaluate(ctx)
        assert decision.action == PolicyAction.DENY
        assert decision.rule_name == "block_critical"

    def test_from_config_disabled(self, risk_scorer):
        policy_data = {"enabled": False}
        engine = PolicyEngine.from_config(policy_data, risk_scorer)
        assert len(engine.rules) == 0
        assert engine.default_action == PolicyAction.ALLOW

    def test_from_config_empty(self, risk_scorer):
        engine = PolicyEngine.from_config({}, risk_scorer)
        assert len(engine.rules) == 0

    def test_deny_decision(self, risk_scorer):
        rules = [
            PolicyRule("block_admin", PolicyAction.DENY, {
                "target_app": ["Registry Editor", "Task Manager"],
            }),
        ]
        engine = PolicyEngine(rules, PolicyAction.ALLOW, risk_scorer)
        ctx = ActionContext(tool="cue_click", target_app="Task Manager")
        decision = engine.evaluate(ctx)
        assert decision.action == PolicyAction.DENY

    def test_warn_decision(self, risk_scorer):
        rules = [
            PolicyRule("warn_high", PolicyAction.WARN, {"risk_level": "HIGH"}),
        ]
        engine = PolicyEngine(rules, PolicyAction.ALLOW, risk_scorer)
        ctx = ActionContext(tool="cue_drag")
        decision = engine.evaluate(ctx)
        assert decision.action == PolicyAction.WARN
        assert decision.risk_level == RiskLevel.HIGH
