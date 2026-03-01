"""CUE policy engine — rule-based action filtering and enforcement."""

from __future__ import annotations

from typing import Any, Optional

from cue.core.models import (
    ActionContext,
    PolicyAction,
    PolicyDecision,
    RiskLevel,
)
from cue.core.risk import RiskScorer


class PolicyRule:
    """A single policy rule loaded from configuration."""

    def __init__(
        self,
        name: str,
        action: PolicyAction,
        conditions: dict[str, Any],
        reason: str = "",
    ) -> None:
        self.name = name
        self.action = action
        self.reason = reason or f"Matched rule: {name}"

        # Pre-process conditions for fast matching
        self._tool: Optional[set[str]] = self._to_set(conditions.get("tool"))
        self._target_app: Optional[set[str]] = self._to_lower_set(
            conditions.get("target_app")
        )
        self._key_combo: Optional[set[tuple[str, ...]]] = None
        raw_combo = conditions.get("key_combo")
        if raw_combo is not None:
            combos = [raw_combo] if isinstance(raw_combo, str) else raw_combo
            self._key_combo = {
                tuple(sorted(c.lower().replace(" ", "").split("+"))) for c in combos
            }
        self._risk_level: Optional[RiskLevel] = None
        raw_risk = conditions.get("risk_level")
        if raw_risk is not None:
            self._risk_level = RiskLevel[raw_risk.upper()] if isinstance(raw_risk, str) else RiskLevel(raw_risk)

    @staticmethod
    def _to_set(value: Any) -> Optional[set[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            return {value}
        return set(value)

    @staticmethod
    def _to_lower_set(value: Any) -> Optional[set[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            return {value.lower()}
        return {v.lower() for v in value}

    def matches(self, ctx: ActionContext, risk_level: RiskLevel) -> bool:
        """Return True if all conditions match the given context."""
        # All specified conditions must match (AND logic)
        if self._tool is not None and ctx.tool not in self._tool:
            return False

        if self._target_app is not None:
            if ctx.target_app is None:
                return False
            app_lower = ctx.target_app.lower()
            if not any(blocked in app_lower for blocked in self._target_app):
                return False

        if self._key_combo is not None:
            if ctx.key_combo is None:
                return False
            parts = tuple(sorted(ctx.key_combo.lower().replace(" ", "").split("+")))
            if parts not in self._key_combo:
                return False

        if self._risk_level is not None and risk_level < self._risk_level:
            return False

        return True


class PolicyEngine:
    """Evaluate actions against a set of safety policies.

    Uses first-match-wins semantics: rules are evaluated in order and the
    first matching rule determines the decision.
    """

    def __init__(
        self,
        rules: list[PolicyRule],
        default_action: PolicyAction = PolicyAction.ALLOW,
        risk_scorer: Optional[RiskScorer] = None,
    ) -> None:
        self.rules = rules
        self.default_action = default_action
        self._risk_scorer = risk_scorer or RiskScorer()

    @classmethod
    def from_config(
        cls,
        policy_data: dict[str, Any],
        risk_scorer: Optional[RiskScorer] = None,
    ) -> "PolicyEngine":
        """Build a PolicyEngine from the 'policies' section of config YAML."""
        if not policy_data or not policy_data.get("enabled", True):
            return cls(rules=[], default_action=PolicyAction.ALLOW, risk_scorer=risk_scorer)

        default_str = policy_data.get("default_action", "allow")
        default_action = PolicyAction(default_str.lower())

        rules: list[PolicyRule] = []
        for rule_data in policy_data.get("rules", []):
            action = PolicyAction(rule_data["action"].lower())
            rules.append(
                PolicyRule(
                    name=rule_data["name"],
                    action=action,
                    conditions=rule_data.get("conditions", {}),
                    reason=rule_data.get("reason", ""),
                )
            )

        return cls(rules=rules, default_action=default_action, risk_scorer=risk_scorer)

    def evaluate(self, ctx: ActionContext) -> PolicyDecision:
        """Evaluate an action context and return a policy decision."""
        risk_level = self._risk_scorer.score(ctx)

        for rule in self.rules:
            if rule.matches(ctx, risk_level):
                return PolicyDecision(
                    action=rule.action,
                    rule_name=rule.name,
                    reason=rule.reason,
                    risk_level=risk_level,
                )

        return PolicyDecision(
            action=self.default_action,
            rule_name="default",
            reason="No matching rule; applying default action.",
            risk_level=risk_level,
        )
