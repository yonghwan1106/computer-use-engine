"""Tests for cue.core.session — session management and action tracking."""

from __future__ import annotations

import pytest

from cue.core.models import PolicyAction, RiskLevel, SessionStatus
from cue.core.session import Session, SessionManager


class TestSession:
    def test_initial_state(self):
        s = Session()
        assert s.status == SessionStatus.ACTIVE
        assert s.action_count == 0
        assert len(s.id) == 16

    def test_custom_id(self):
        s = Session(session_id="test-session-1")
        assert s.id == "test-session-1"

    def test_record_action(self):
        s = Session()
        record = s.record_action(tool="cue_click", params={"x": 100, "y": 200})
        assert record.tool == "cue_click"
        assert s.action_count == 1

    def test_record_multiple(self):
        s = Session()
        s.record_action(tool="cue_click")
        s.record_action(tool="cue_type")
        s.record_action(tool="cue_screenshot")
        assert s.action_count == 3

    def test_history_is_copy(self):
        s = Session()
        s.record_action(tool="cue_click")
        h = s.history
        h.clear()
        assert s.action_count == 1

    def test_action_limit(self):
        s = Session(max_actions=2)
        s.record_action(tool="cue_click")
        s.record_action(tool="cue_type")
        with pytest.raises(RuntimeError, match="limit reached"):
            s.record_action(tool="cue_screenshot")

    def test_unlimited_actions(self):
        s = Session(max_actions=0)
        for _ in range(200):
            s.record_action(tool="cue_click")
        assert s.action_count == 200

    def test_pause_resume(self):
        s = Session()
        s.pause()
        assert s.status == SessionStatus.PAUSED
        with pytest.raises(RuntimeError, match="paused"):
            s.record_action(tool="cue_click")
        s.resume()
        assert s.status == SessionStatus.ACTIVE
        s.record_action(tool="cue_click")
        assert s.action_count == 1

    def test_pause_when_not_active(self):
        s = Session()
        s.terminate()
        with pytest.raises(RuntimeError, match="terminated"):
            s.pause()

    def test_resume_when_not_paused(self):
        s = Session()
        with pytest.raises(RuntimeError, match="active"):
            s.resume()

    def test_terminate(self):
        s = Session()
        s.terminate()
        assert s.status == SessionStatus.TERMINATED
        with pytest.raises(RuntimeError, match="terminated"):
            s.record_action(tool="cue_click")

    def test_terminate_idempotent(self):
        s = Session()
        s.terminate()
        s.terminate()  # no error
        assert s.status == SessionStatus.TERMINATED

    def test_summary(self):
        s = Session(session_id="sum-test")
        s.record_action(tool="cue_screenshot", risk_level=RiskLevel.LOW)
        s.record_action(tool="cue_click", risk_level=RiskLevel.MEDIUM)
        s.record_action(tool="cue_key", risk_level=RiskLevel.HIGH, error="timeout")
        summary = s.summary()
        assert summary["session_id"] == "sum-test"
        assert summary["action_count"] == 3
        assert summary["error_count"] == 1
        assert summary["risk_breakdown"]["LOW"] == 1
        assert summary["risk_breakdown"]["MEDIUM"] == 1
        assert summary["risk_breakdown"]["HIGH"] == 1
        assert summary["risk_breakdown"]["CRITICAL"] == 0


class TestSessionManager:
    def test_start_session(self):
        mgr = SessionManager()
        session = mgr.start_session()
        assert session.status == SessionStatus.ACTIVE
        assert mgr.current_session is session

    def test_ensure_session_auto_start(self):
        mgr = SessionManager()
        assert mgr.current_session is None
        session = mgr.ensure_session()
        assert session.status == SessionStatus.ACTIVE

    def test_ensure_session_reuses_active(self):
        mgr = SessionManager()
        s1 = mgr.ensure_session()
        s2 = mgr.ensure_session()
        assert s1.id == s2.id

    def test_start_terminates_previous(self):
        mgr = SessionManager()
        s1 = mgr.start_session()
        s2 = mgr.start_session()
        assert s1.status == SessionStatus.TERMINATED
        assert s2.status == SessionStatus.ACTIVE
        assert mgr.current_session is s2

    def test_record_action(self):
        mgr = SessionManager()
        record = mgr.record_action(tool="cue_click")
        assert record.tool == "cue_click"
        assert mgr.action_count == 1

    def test_action_count_no_session(self):
        mgr = SessionManager()
        assert mgr.action_count == 0

    def test_max_actions_enforced(self):
        mgr = SessionManager(max_actions=3)
        mgr.record_action(tool="cue_click")
        mgr.record_action(tool="cue_type")
        mgr.record_action(tool="cue_key")
        with pytest.raises(RuntimeError, match="limit reached"):
            mgr.record_action(tool="cue_screenshot")

    def test_reset(self):
        mgr = SessionManager()
        mgr.record_action(tool="cue_click")
        mgr.reset()
        assert mgr.action_count == 0
        assert mgr.current_session is None

    def test_get_history(self):
        mgr = SessionManager()
        mgr.record_action(tool="cue_click")
        mgr.start_session()
        mgr.record_action(tool="cue_type")
        history = mgr.get_history()
        assert len(history) == 2
        assert history[0]["action_count"] == 1
        assert history[1]["action_count"] == 1

    def test_record_with_risk_and_decision(self):
        mgr = SessionManager()
        record = mgr.record_action(
            tool="cue_key",
            risk_level=RiskLevel.HIGH,
            decision=PolicyAction.WARN,
        )
        assert record.risk_level == RiskLevel.HIGH
        assert record.decision == PolicyAction.WARN
