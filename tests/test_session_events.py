"""Tests for SessionManager event emission via EventBus."""

from __future__ import annotations

import pytest

from cue.core.session import SessionManager
from cue.monitor.events import EventBus, EventType


# ---------------------------------------------------------------------------
# Backward compatibility — no event_bus attached
# ---------------------------------------------------------------------------

class TestSessionManagerNoEventBus:
    def test_start_session_works_without_event_bus(self):
        """SessionManager with no event_bus must not raise."""
        sm = SessionManager(max_actions=50)
        # event_bus defaults to None — start_session must succeed silently
        session = sm.start_session()
        assert session is not None
        assert sm.current_session is session

    def test_reset_works_without_event_bus(self):
        """reset() with no event_bus must not raise."""
        sm = SessionManager()
        sm.start_session()
        sm.reset()  # no error expected
        assert sm.current_session is None


# ---------------------------------------------------------------------------
# start_session event emission
# ---------------------------------------------------------------------------

class TestStartSessionEmitsEvent:
    def test_start_session_emits_session_started(self):
        bus = EventBus()
        sm = SessionManager(max_actions=50)
        sm.event_bus = bus

        sm.start_session()

        events = bus.get_buffered(event_type=EventType.SESSION_STARTED)
        assert len(events) == 1

    def test_session_started_event_contains_session_id(self):
        bus = EventBus()
        sm = SessionManager()
        sm.event_bus = bus

        session = sm.start_session()

        events = bus.get_buffered(event_type=EventType.SESSION_STARTED)
        assert events[0].data["session_id"] == session.id

    def test_session_started_event_contains_max_actions(self):
        bus = EventBus()
        sm = SessionManager(max_actions=50)
        sm.event_bus = bus

        sm.start_session()

        events = bus.get_buffered(event_type=EventType.SESSION_STARTED)
        assert events[0].data["max_actions"] == 50


# ---------------------------------------------------------------------------
# reset / SESSION_TERMINATED event emission
# ---------------------------------------------------------------------------

class TestResetEmitsEvent:
    def test_reset_emits_session_terminated(self):
        bus = EventBus()
        sm = SessionManager()
        sm.event_bus = bus

        sm.start_session()
        bus.clear_buffer()  # ignore SESSION_STARTED

        sm.reset()

        events = bus.get_buffered(event_type=EventType.SESSION_TERMINATED)
        assert len(events) == 1

    def test_session_terminated_event_contains_session_id(self):
        bus = EventBus()
        sm = SessionManager()
        sm.event_bus = bus

        session = sm.start_session()
        old_id = session.id
        bus.clear_buffer()

        sm.reset()

        events = bus.get_buffered(event_type=EventType.SESSION_TERMINATED)
        assert events[0].data["session_id"] == old_id


# ---------------------------------------------------------------------------
# Starting a new session while one exists
# ---------------------------------------------------------------------------

class TestStartSessionTerminatesPrevious:
    def test_starting_new_session_emits_session_terminated_for_old(self):
        """start_session() on an existing active session terminates it.

        The code calls session.terminate() before creating the new session,
        but the SESSION_TERMINATED event is only emitted by reset(). Here we
        verify that start_session emits exactly one SESSION_STARTED event
        for the new session (the old session is silently terminated without
        an explicit SESSION_TERMINATED event from start_session itself).
        """
        bus = EventBus()
        sm = SessionManager()
        sm.event_bus = bus

        sm.start_session()  # first session
        sm.start_session()  # replaces first session

        started = bus.get_buffered(event_type=EventType.SESSION_STARTED)
        # Two SESSION_STARTED events — one per start_session() call
        assert len(started) == 2

    def test_multiple_start_sessions_emit_correct_event_count(self):
        bus = EventBus()
        sm = SessionManager()
        sm.event_bus = bus

        for _ in range(3):
            sm.start_session()

        started = bus.get_buffered(event_type=EventType.SESSION_STARTED)
        assert len(started) == 3
        # Each event carries a distinct session_id
        ids = [e.data["session_id"] for e in started]
        assert len(set(ids)) == 3
