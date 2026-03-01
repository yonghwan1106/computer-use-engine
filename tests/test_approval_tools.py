"""Tests for cue.tools.approval — MCP approval tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cue.core.approval import ApprovalManager, ApprovalRequest, ApprovalStatus
from cue.monitor.events import EventBus, EventType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def approval_manager():
    return ApprovalManager(timeout=300.0, grant_ttl=60.0)


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def _patch_server(approval_manager, event_bus):
    """Patch cue.server module-level vars for tool functions."""
    with patch("cue.tools.approval._server") as mock_server:
        mock_server.approval_manager = approval_manager
        mock_server.event_bus = event_bus
        yield mock_server


# ---------------------------------------------------------------------------
# cue_pending_approvals
# ---------------------------------------------------------------------------

def test_pending_approvals_empty(_patch_server, approval_manager):
    from cue.tools.approval import cue_pending_approvals
    assert cue_pending_approvals() == []


def test_pending_approvals_lists_pending(_patch_server, approval_manager):
    from cue.tools.approval import cue_pending_approvals
    r = approval_manager.create_request(tool="cue_click", reason="risky")
    result = cue_pending_approvals()
    assert len(result) == 1
    assert result[0]["id"] == r.id
    assert result[0]["tool"] == "cue_click"
    assert result[0]["reason"] == "risky"


def test_pending_approvals_excludes_resolved(_patch_server, approval_manager):
    from cue.tools.approval import cue_pending_approvals
    r1 = approval_manager.create_request(tool="cue_click")
    r2 = approval_manager.create_request(tool="cue_key")
    approval_manager.approve(r1.id)
    result = cue_pending_approvals()
    assert len(result) == 1
    assert result[0]["id"] == r2.id


def test_pending_approvals_no_manager():
    from cue.tools.approval import cue_pending_approvals
    with patch("cue.tools.approval._server") as mock_server:
        mock_server.approval_manager = None
        assert cue_pending_approvals() == []


# ---------------------------------------------------------------------------
# cue_approve_action
# ---------------------------------------------------------------------------

def test_approve_action_success(_patch_server, approval_manager, event_bus):
    from cue.tools.approval import cue_approve_action
    r = approval_manager.create_request(tool="cue_click", reason="test")
    result = cue_approve_action(r.id, reason="looks safe")
    assert result["status"] == "approved"
    assert result["request_id"] == r.id
    assert result["tool"] == "cue_click"
    # Verify event emitted
    events = event_bus.get_buffered(event_type=EventType.APPROVAL_GRANTED)
    assert len(events) == 1
    assert events[0].data["request_id"] == r.id


def test_approve_action_unknown_request(_patch_server):
    from cue.tools.approval import cue_approve_action
    result = cue_approve_action("nonexistent")
    assert "error" in result


def test_approve_action_already_approved(_patch_server, approval_manager):
    from cue.tools.approval import cue_approve_action
    r = approval_manager.create_request(tool="cue_click")
    cue_approve_action(r.id)
    result = cue_approve_action(r.id)
    assert "error" in result


def test_approve_action_no_manager():
    from cue.tools.approval import cue_approve_action
    with patch("cue.tools.approval._server") as mock_server:
        mock_server.approval_manager = None
        result = cue_approve_action("abc")
        assert result["error"] == "Approval system not initialized."


# ---------------------------------------------------------------------------
# cue_deny_action
# ---------------------------------------------------------------------------

def test_deny_action_success(_patch_server, approval_manager, event_bus):
    from cue.tools.approval import cue_deny_action
    r = approval_manager.create_request(tool="cue_click", reason="test")
    result = cue_deny_action(r.id, reason="too risky")
    assert result["status"] == "denied"
    assert result["request_id"] == r.id
    # Verify event emitted
    events = event_bus.get_buffered(event_type=EventType.APPROVAL_DENIED)
    assert len(events) == 1
    assert events[0].data["request_id"] == r.id


def test_deny_action_unknown_request(_patch_server):
    from cue.tools.approval import cue_deny_action
    result = cue_deny_action("nonexistent")
    assert "error" in result


def test_deny_action_no_manager():
    from cue.tools.approval import cue_deny_action
    with patch("cue.tools.approval._server") as mock_server:
        mock_server.approval_manager = None
        result = cue_deny_action("abc")
        assert result["error"] == "Approval system not initialized."
