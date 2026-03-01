"""Tests for cue.core.approval — ApprovalManager, ApprovalRequest, ApprovalGrant."""

from __future__ import annotations

import time

import pytest

from cue.core.approval import (
    ApprovalGrant,
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
)


# ---------------------------------------------------------------------------
# ApprovalStatus enum
# ---------------------------------------------------------------------------

def test_approval_status_has_four_values():
    assert len(ApprovalStatus) == 4


def test_approval_status_members():
    assert {s.value for s in ApprovalStatus} == {"pending", "approved", "denied", "expired"}


# ---------------------------------------------------------------------------
# ApprovalRequest dataclass
# ---------------------------------------------------------------------------

def test_approval_request_defaults():
    r = ApprovalRequest()
    assert r.status == ApprovalStatus.PENDING
    assert isinstance(r.id, str)
    assert len(r.id) == 12
    assert r.tool == ""
    assert r.params == {}
    assert r.target_app is None
    assert r.key_combo is None
    assert r.resolved_at is None
    assert r.resolution_reason is None


def test_approval_request_custom_fields():
    r = ApprovalRequest(
        tool="cue_click",
        params={"x": 100, "y": 200},
        reason="High-risk click",
        rule_name="hold_clicks",
        risk_level="HIGH",
        target_app="notepad",
    )
    assert r.tool == "cue_click"
    assert r.params == {"x": 100, "y": 200}
    assert r.reason == "High-risk click"
    assert r.rule_name == "hold_clicks"
    assert r.risk_level == "HIGH"
    assert r.target_app == "notepad"


def test_approval_request_unique_ids():
    r1 = ApprovalRequest()
    r2 = ApprovalRequest()
    assert r1.id != r2.id


# ---------------------------------------------------------------------------
# ApprovalGrant dataclass
# ---------------------------------------------------------------------------

def test_approval_grant_defaults():
    g = ApprovalGrant()
    assert g.consumed is False
    assert g.request_id == ""
    assert g.tool == ""


# ---------------------------------------------------------------------------
# ApprovalManager — create_request
# ---------------------------------------------------------------------------

@pytest.fixture
def manager():
    return ApprovalManager(timeout=300.0, grant_ttl=60.0)


def test_create_request_returns_pending_request(manager):
    r = manager.create_request(tool="cue_click", reason="test")
    assert r.status == ApprovalStatus.PENDING
    assert r.tool == "cue_click"
    assert r.reason == "test"


def test_create_request_stores_in_requests(manager):
    r = manager.create_request(tool="cue_click")
    assert manager.get_request(r.id) is r


def test_create_request_with_all_fields(manager):
    r = manager.create_request(
        tool="cue_key",
        params={"key": "enter"},
        reason="risky",
        rule_name="hold_keys",
        risk_level="HIGH",
        target_app="terminal",
        key_combo="ctrl+c",
    )
    assert r.tool == "cue_key"
    assert r.params == {"key": "enter"}
    assert r.target_app == "terminal"
    assert r.key_combo == "ctrl+c"
    assert r.rule_name == "hold_keys"
    assert r.risk_level == "HIGH"


# ---------------------------------------------------------------------------
# ApprovalManager — approve
# ---------------------------------------------------------------------------

def test_approve_changes_status(manager):
    r = manager.create_request(tool="cue_click", reason="test")
    manager.approve(r.id, reason="looks safe")
    assert r.status == ApprovalStatus.APPROVED
    assert r.resolved_at is not None
    assert r.resolution_reason == "looks safe"


def test_approve_returns_grant(manager):
    r = manager.create_request(tool="cue_click", params={"x": 10})
    grant = manager.approve(r.id)
    assert isinstance(grant, ApprovalGrant)
    assert grant.request_id == r.id
    assert grant.tool == "cue_click"
    assert grant.params == {"x": 10}
    assert grant.consumed is False
    assert grant.expires_at > grant.created_at


def test_approve_grant_ttl(manager):
    r = manager.create_request(tool="cue_click")
    grant = manager.approve(r.id)
    assert grant.expires_at == pytest.approx(grant.created_at + 60.0, abs=1.0)


def test_approve_unknown_request_raises_key_error(manager):
    with pytest.raises(KeyError, match="not found"):
        manager.approve("nonexistent")


def test_approve_already_approved_raises_value_error(manager):
    r = manager.create_request(tool="cue_click")
    manager.approve(r.id)
    with pytest.raises(ValueError, match="approved"):
        manager.approve(r.id)


def test_approve_denied_request_raises_value_error(manager):
    r = manager.create_request(tool="cue_click")
    manager.deny(r.id)
    with pytest.raises(ValueError, match="denied"):
        manager.approve(r.id)


# ---------------------------------------------------------------------------
# ApprovalManager — deny
# ---------------------------------------------------------------------------

def test_deny_changes_status(manager):
    r = manager.create_request(tool="cue_click", reason="test")
    manager.deny(r.id, reason="too risky")
    assert r.status == ApprovalStatus.DENIED
    assert r.resolved_at is not None
    assert r.resolution_reason == "too risky"


def test_deny_unknown_request_raises_key_error(manager):
    with pytest.raises(KeyError, match="not found"):
        manager.deny("nonexistent")


def test_deny_already_denied_raises_value_error(manager):
    r = manager.create_request(tool="cue_click")
    manager.deny(r.id)
    with pytest.raises(ValueError, match="denied"):
        manager.deny(r.id)


def test_deny_approved_request_raises_value_error(manager):
    r = manager.create_request(tool="cue_click")
    manager.approve(r.id)
    with pytest.raises(ValueError, match="approved"):
        manager.deny(r.id)


# ---------------------------------------------------------------------------
# ApprovalManager — get_pending
# ---------------------------------------------------------------------------

def test_get_pending_returns_only_pending(manager):
    r1 = manager.create_request(tool="cue_click")
    r2 = manager.create_request(tool="cue_key")
    r3 = manager.create_request(tool="cue_scroll")
    manager.approve(r1.id)
    manager.deny(r2.id)
    pending = manager.get_pending()
    assert len(pending) == 1
    assert pending[0].id == r3.id


def test_get_pending_empty_when_none(manager):
    assert manager.get_pending() == []


# ---------------------------------------------------------------------------
# ApprovalManager — get_request
# ---------------------------------------------------------------------------

def test_get_request_returns_none_for_unknown(manager):
    assert manager.get_request("nonexistent") is None


def test_get_request_returns_correct_request(manager):
    r = manager.create_request(tool="cue_click")
    assert manager.get_request(r.id) is r


# ---------------------------------------------------------------------------
# ApprovalManager — check_grant
# ---------------------------------------------------------------------------

def test_check_grant_returns_none_when_no_grants(manager):
    assert manager.check_grant(tool="cue_click") is None


def test_check_grant_consumes_matching_grant(manager):
    r = manager.create_request(tool="cue_click", params={"x": 10})
    manager.approve(r.id)
    grant = manager.check_grant(tool="cue_click")
    assert grant is not None
    assert grant.consumed is True
    assert grant.request_id == r.id


def test_check_grant_returns_none_after_consumed(manager):
    r = manager.create_request(tool="cue_click")
    manager.approve(r.id)
    manager.check_grant(tool="cue_click")  # consume
    assert manager.check_grant(tool="cue_click") is None


def test_check_grant_does_not_match_wrong_tool(manager):
    r = manager.create_request(tool="cue_click")
    manager.approve(r.id)
    assert manager.check_grant(tool="cue_key") is None


def test_check_grant_ignores_expired_grants(manager):
    mgr = ApprovalManager(timeout=300.0, grant_ttl=0.0)  # instant expiry
    r = mgr.create_request(tool="cue_click")
    mgr.approve(r.id)
    # Grant has already expired (ttl=0)
    assert mgr.check_grant(tool="cue_click") is None


# ---------------------------------------------------------------------------
# ApprovalManager — _expire_stale (lazy expiration)
# ---------------------------------------------------------------------------

def test_expire_stale_marks_timed_out_requests(manager):
    mgr = ApprovalManager(timeout=0.0, grant_ttl=60.0)  # instant timeout
    r = mgr.create_request(tool="cue_click")
    # Trigger lazy expiration
    pending = mgr.get_pending()
    assert len(pending) == 0
    assert r.status == ApprovalStatus.EXPIRED
    assert r.resolved_at is not None


def test_expire_stale_does_not_affect_resolved():
    mgr = ApprovalManager(timeout=300.0, grant_ttl=60.0)
    r = mgr.create_request(tool="cue_click")
    mgr.approve(r.id)
    # Manually shrink timeout to 0 after approval
    mgr.timeout = 0.0
    mgr._expire_stale()
    # Already approved — status must not change to EXPIRED
    assert r.status == ApprovalStatus.APPROVED


def test_expire_stale_called_during_approve(manager):
    mgr = ApprovalManager(timeout=0.0, grant_ttl=60.0)
    r1 = mgr.create_request(tool="cue_click")
    r2 = mgr.create_request(tool="cue_key")
    # r1 and r2 both expired by timeout=0, approve should fail
    with pytest.raises(ValueError, match="expired"):
        mgr.approve(r1.id)


# ---------------------------------------------------------------------------
# ApprovalManager — custom timeouts
# ---------------------------------------------------------------------------

def test_custom_timeout_and_grant_ttl():
    mgr = ApprovalManager(timeout=10.0, grant_ttl=5.0)
    assert mgr.timeout == 10.0
    assert mgr.grant_ttl == 5.0


def test_default_timeout_and_grant_ttl():
    mgr = ApprovalManager()
    assert mgr.timeout == 300.0
    assert mgr.grant_ttl == 60.0


# ---------------------------------------------------------------------------
# ApprovalManager — grant params isolation
# ---------------------------------------------------------------------------

def test_grant_params_are_copied(manager):
    """Modifying the original request params should not affect the grant."""
    params = {"x": 10, "y": 20}
    r = manager.create_request(tool="cue_click", params=params)
    grant = manager.approve(r.id)
    params["x"] = 999
    assert grant.params == {"x": 10, "y": 20}
