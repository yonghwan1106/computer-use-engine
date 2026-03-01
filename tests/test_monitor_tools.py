"""Tests for cue.tools.monitor — session status, recent events, safety summary."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from cue.monitor.events import Event, EventBus, EventType


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def mock_server(event_bus):
    """Patch cue.server module-level attributes for monitor tools."""
    mock_session = MagicMock()
    mock_session.summary.return_value = {
        "session_id": "test123",
        "status": "active",
        "action_count": 5,
        "risk_breakdown": {"LOW": 3, "MEDIUM": 1, "HIGH": 1, "CRITICAL": 0},
        "error_count": 0,
    }
    mock_sm = MagicMock()
    mock_sm.current_session = mock_session

    mock_guardrails = MagicMock()
    mock_guardrails._session_manager = mock_sm

    with patch("cue.tools.monitor._server") as srv:
        srv.event_bus = event_bus
        srv.guardrails = mock_guardrails
        yield srv, event_bus


# ---------------------------------------------------------------------------
# cue_session_status
# ---------------------------------------------------------------------------

class TestCueSessionStatus:
    def test_returns_summary_when_session_exists(self, mock_server):
        from cue.tools.monitor import cue_session_status

        srv, _ = mock_server
        result = cue_session_status()

        assert result["session_id"] == "test123"
        assert result["status"] == "active"
        assert result["action_count"] == 5

    def test_returns_no_session_when_current_session_is_none(self, mock_server):
        from cue.tools.monitor import cue_session_status

        srv, _ = mock_server
        srv.guardrails._session_manager.current_session = None

        result = cue_session_status()

        assert result["status"] == "no_session"
        assert result["action_count"] == 0

    def test_returns_error_when_safety_system_not_initialized(self, event_bus):
        from cue.tools.monitor import cue_session_status

        with patch("cue.tools.monitor._server") as srv:
            srv.guardrails = None
            result = cue_session_status()

        assert "error" in result
        assert "not initialized" in result["error"]


# ---------------------------------------------------------------------------
# cue_recent_events
# ---------------------------------------------------------------------------

class TestCueRecentEvents:
    def test_returns_empty_list_when_no_events(self, mock_server):
        from cue.tools.monitor import cue_recent_events

        result = cue_recent_events()

        assert result == []

    def test_returns_events_newest_first(self, mock_server):
        from cue.tools.monitor import cue_recent_events

        _, bus = mock_server
        bus.emit(Event(type=EventType.ACTION_STARTED, data={"order": 1}))
        bus.emit(Event(type=EventType.ACTION_COMPLETED, data={"order": 2}))
        bus.emit(Event(type=EventType.ACTION_DENIED, data={"order": 3}))

        result = cue_recent_events()

        assert len(result) == 3
        # Newest first: order 3, 2, 1
        assert result[0]["data"]["order"] == 3
        assert result[1]["data"]["order"] == 2
        assert result[2]["data"]["order"] == 1

    def test_respects_count_parameter(self, mock_server):
        from cue.tools.monitor import cue_recent_events

        _, bus = mock_server
        for i in range(10):
            bus.emit(Event(type=EventType.ACTION_STARTED, data={"i": i}))

        result = cue_recent_events(count=3)

        assert len(result) == 3
        # Should be the 3 most recent (i=9, 8, 7)
        assert result[0]["data"]["i"] == 9
        assert result[1]["data"]["i"] == 8
        assert result[2]["data"]["i"] == 7

    def test_filters_by_event_type(self, mock_server):
        from cue.tools.monitor import cue_recent_events

        _, bus = mock_server
        bus.emit(Event(type=EventType.ACTION_STARTED, data={}))
        bus.emit(Event(type=EventType.ACTION_DENIED, data={"tool": "cue_click"}))
        bus.emit(Event(type=EventType.ACTION_STARTED, data={}))

        result = cue_recent_events(event_type="action_denied")

        assert len(result) == 1
        assert result[0]["type"] == "action_denied"

    def test_returns_error_for_unknown_event_type(self, mock_server):
        from cue.tools.monitor import cue_recent_events

        result = cue_recent_events(event_type="nonexistent_type")

        assert len(result) == 1
        assert "error" in result[0]
        assert "Unknown event type" in result[0]["error"]


# ---------------------------------------------------------------------------
# cue_safety_summary
# ---------------------------------------------------------------------------

class TestCueSafetySummary:
    def test_returns_correct_denied_and_alert_counts(self, mock_server):
        from cue.tools.monitor import cue_safety_summary

        _, bus = mock_server
        bus.emit(Event(type=EventType.ACTION_DENIED, data={"tool": "cue_key", "rule_name": "r1", "reason": "blocked"}))
        bus.emit(Event(type=EventType.ACTION_DENIED, data={"tool": "cue_type", "rule_name": "r2", "reason": "blocked"}))
        bus.emit(Event(type=EventType.RISK_ALERT, data={}))
        bus.emit(Event(type=EventType.ACTION_COMPLETED, data={}))

        result = cue_safety_summary()

        assert result["denied_count"] == 2
        assert result["alert_count"] == 1
        assert result["total_events"] == 4

    def test_returns_recent_denials_list_capped_at_ten(self, mock_server):
        from cue.tools.monitor import cue_safety_summary

        _, bus = mock_server
        for i in range(15):
            bus.emit(Event(
                type=EventType.ACTION_DENIED,
                data={"tool": f"tool_{i}", "rule_name": f"rule_{i}", "reason": "blocked"},
            ))

        result = cue_safety_summary()

        assert result["denied_count"] == 15
        # recent_denials capped at 10 (last 10)
        assert len(result["recent_denials"]) == 10
        # Last emitted denial should appear in the list
        assert result["recent_denials"][-1]["tool"] == "tool_14"

    def test_recent_denials_contain_expected_fields(self, mock_server):
        from cue.tools.monitor import cue_safety_summary

        _, bus = mock_server
        bus.emit(Event(
            type=EventType.ACTION_DENIED,
            data={"tool": "cue_key", "rule_name": "blocked_keys", "reason": "Key combo blocked"},
        ))

        result = cue_safety_summary()

        denial = result["recent_denials"][0]
        assert denial["tool"] == "cue_key"
        assert denial["rule_name"] == "blocked_keys"
        assert denial["reason"] == "Key combo blocked"
        assert "timestamp" in denial
