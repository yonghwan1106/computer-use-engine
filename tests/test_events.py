"""Tests for cue.monitor.events — EventType, Event, and EventBus."""

from __future__ import annotations

import asyncio
import dataclasses
import time

import pytest

from cue.monitor.events import Event, EventBus, EventType


# ---------------------------------------------------------------------------
# 1. EventType enum has all 10 values
# ---------------------------------------------------------------------------

def test_event_type_has_fourteen_values():
    assert len(EventType) == 14


def test_event_type_members():
    names = {e.name for e in EventType}
    expected = {
        "ACTION_STARTED",
        "ACTION_COMPLETED",
        "ACTION_DENIED",
        "POLICY_DECISION",
        "RISK_ALERT",
        "SESSION_STARTED",
        "SESSION_PAUSED",
        "SESSION_RESUMED",
        "SESSION_TERMINATED",
        "GUARDRAIL_TRIGGERED",
        "APPROVAL_REQUIRED",
        "APPROVAL_GRANTED",
        "APPROVAL_DENIED",
        "APPROVAL_EXPIRED",
    }
    assert names == expected


# ---------------------------------------------------------------------------
# 2. Event creation with auto-generated id and timestamp
# ---------------------------------------------------------------------------

def test_event_auto_id_and_timestamp():
    before = time.time()
    event = Event(type=EventType.ACTION_STARTED)
    after = time.time()

    assert isinstance(event.id, str)
    assert len(event.id) == 16
    assert before <= event.timestamp <= after


def test_event_ids_are_unique():
    e1 = Event(type=EventType.ACTION_STARTED)
    e2 = Event(type=EventType.ACTION_STARTED)
    assert e1.id != e2.id


# ---------------------------------------------------------------------------
# 3. Event is frozen (immutable)
# ---------------------------------------------------------------------------

def test_event_is_frozen():
    event = Event(type=EventType.RISK_ALERT)
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        event.type = EventType.ACTION_DENIED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 4. EventBus init with default buffer_size
# ---------------------------------------------------------------------------

def test_eventbus_default_buffer_size():
    bus = EventBus()
    assert bus._buffer.maxlen == 1000


# ---------------------------------------------------------------------------
# 5. EventBus init with custom buffer_size
# ---------------------------------------------------------------------------

def test_eventbus_custom_buffer_size():
    bus = EventBus(buffer_size=42)
    assert bus._buffer.maxlen == 42


# ---------------------------------------------------------------------------
# 6. subscribe + emit calls the subscriber
# ---------------------------------------------------------------------------

def test_subscribe_and_emit():
    bus = EventBus()
    received = []
    bus.subscribe(lambda e: received.append(e))
    event = Event(type=EventType.ACTION_STARTED)
    bus.emit(event)
    assert len(received) == 1
    assert received[0] is event


# ---------------------------------------------------------------------------
# 7. subscribe with event_type filter — only receives matching events
# ---------------------------------------------------------------------------

def test_subscribe_with_filter_receives_matching():
    bus = EventBus()
    received = []
    bus.subscribe(lambda e: received.append(e), event_type=EventType.RISK_ALERT)
    event = Event(type=EventType.RISK_ALERT)
    bus.emit(event)
    assert len(received) == 1
    assert received[0] is event


# ---------------------------------------------------------------------------
# 8. subscribe with event_type filter — ignores non-matching events
# ---------------------------------------------------------------------------

def test_subscribe_with_filter_ignores_non_matching():
    bus = EventBus()
    received = []
    bus.subscribe(lambda e: received.append(e), event_type=EventType.RISK_ALERT)
    bus.emit(Event(type=EventType.ACTION_STARTED))
    bus.emit(Event(type=EventType.SESSION_TERMINATED))
    assert received == []


# ---------------------------------------------------------------------------
# 9. Multiple subscribers all get called
# ---------------------------------------------------------------------------

def test_multiple_subscribers_all_called():
    bus = EventBus()
    received_a = []
    received_b = []
    bus.subscribe(lambda e: received_a.append(e))
    bus.subscribe(lambda e: received_b.append(e))
    event = Event(type=EventType.POLICY_DECISION)
    bus.emit(event)
    assert len(received_a) == 1
    assert len(received_b) == 1
    assert received_a[0] is event
    assert received_b[0] is event


# ---------------------------------------------------------------------------
# 10. unsubscribe removes the subscriber
# ---------------------------------------------------------------------------

def test_unsubscribe_removes_subscriber():
    bus = EventBus()
    received = []

    def callback(e: Event) -> None:
        received.append(e)

    bus.subscribe(callback)
    bus.unsubscribe(callback)
    bus.emit(Event(type=EventType.ACTION_COMPLETED))
    assert received == []


# ---------------------------------------------------------------------------
# 11. unsubscribe only removes the specific callback
# ---------------------------------------------------------------------------

def test_unsubscribe_only_removes_specific_callback():
    bus = EventBus()
    received_a = []
    received_b = []

    def cb_a(e: Event) -> None:
        received_a.append(e)

    def cb_b(e: Event) -> None:
        received_b.append(e)

    bus.subscribe(cb_a)
    bus.subscribe(cb_b)
    bus.unsubscribe(cb_a)

    bus.emit(Event(type=EventType.ACTION_DENIED))
    assert received_a == []
    assert len(received_b) == 1


# ---------------------------------------------------------------------------
# 12. Subscriber exception does not crash emit
# ---------------------------------------------------------------------------

def test_subscriber_exception_does_not_crash_emit():
    bus = EventBus()
    received = []

    def bad_callback(e: Event) -> None:
        raise ValueError("intentional error")

    def good_callback(e: Event) -> None:
        received.append(e)

    bus.subscribe(bad_callback)
    bus.subscribe(good_callback)

    event = Event(type=EventType.GUARDRAIL_TRIGGERED)
    bus.emit(event)  # must not raise
    assert len(received) == 1


# ---------------------------------------------------------------------------
# 13. emit stores events in buffer
# ---------------------------------------------------------------------------

def test_emit_stores_event_in_buffer():
    bus = EventBus()
    event = Event(type=EventType.SESSION_STARTED)
    bus.emit(event)
    assert event in bus._buffer


# ---------------------------------------------------------------------------
# 14. Buffer respects maxlen (ring buffer behavior)
# ---------------------------------------------------------------------------

def test_buffer_respects_maxlen():
    bus = EventBus(buffer_size=3)
    events = [Event(type=EventType.ACTION_STARTED) for _ in range(5)]
    for e in events:
        bus.emit(e)
    buffered = list(bus._buffer)
    assert len(buffered) == 3
    # Oldest events are evicted; the last 3 remain
    assert buffered == events[-3:]


# ---------------------------------------------------------------------------
# 15. get_buffered returns all events
# ---------------------------------------------------------------------------

def test_get_buffered_returns_all_events():
    bus = EventBus()
    e1 = Event(type=EventType.ACTION_STARTED)
    e2 = Event(type=EventType.ACTION_COMPLETED)
    bus.emit(e1)
    bus.emit(e2)
    result = bus.get_buffered()
    assert e1 in result
    assert e2 in result
    assert len(result) == 2


# ---------------------------------------------------------------------------
# 16. get_buffered with since filter
# ---------------------------------------------------------------------------

def test_get_buffered_since_filter():
    bus = EventBus()
    old_event = Event(type=EventType.ACTION_STARTED, timestamp=1000.0)  # type: ignore[call-arg]
    new_event = Event(type=EventType.ACTION_COMPLETED, timestamp=2000.0)  # type: ignore[call-arg]

    # Bypass emit to inject controlled timestamps directly into buffer
    bus._buffer.append(old_event)
    bus._buffer.append(new_event)

    result = bus.get_buffered(since=1500.0)
    assert old_event not in result
    assert new_event in result


# ---------------------------------------------------------------------------
# 17. get_buffered with event_type filter
# ---------------------------------------------------------------------------

def test_get_buffered_event_type_filter():
    bus = EventBus()
    e1 = Event(type=EventType.RISK_ALERT)
    e2 = Event(type=EventType.SESSION_PAUSED)
    bus.emit(e1)
    bus.emit(e2)

    result = bus.get_buffered(event_type=EventType.RISK_ALERT)
    assert e1 in result
    assert e2 not in result


# ---------------------------------------------------------------------------
# 18. get_buffered with both since and event_type filter
# ---------------------------------------------------------------------------

def test_get_buffered_since_and_type_filter():
    bus = EventBus()
    old_alert = Event(type=EventType.RISK_ALERT, timestamp=100.0)  # type: ignore[call-arg]
    new_alert = Event(type=EventType.RISK_ALERT, timestamp=300.0)  # type: ignore[call-arg]
    new_other = Event(type=EventType.ACTION_DENIED, timestamp=300.0)  # type: ignore[call-arg]

    bus._buffer.extend([old_alert, new_alert, new_other])

    result = bus.get_buffered(since=200.0, event_type=EventType.RISK_ALERT)
    assert old_alert not in result
    assert new_alert in result
    assert new_other not in result


# ---------------------------------------------------------------------------
# 19. clear_buffer empties the buffer
# ---------------------------------------------------------------------------

def test_clear_buffer():
    bus = EventBus()
    bus.emit(Event(type=EventType.SESSION_RESUMED))
    bus.emit(Event(type=EventType.SESSION_TERMINATED))
    bus.clear_buffer()
    assert list(bus._buffer) == []
    assert bus.get_buffered() == []


# ---------------------------------------------------------------------------
# 20. subscribe_async registers async subscriber (basic registration test)
# ---------------------------------------------------------------------------

def test_subscribe_async_registers():
    bus = EventBus()

    async def async_cb(e: Event) -> None:
        pass

    assert len(bus._async_subscribers) == 0
    bus.subscribe_async(async_cb)
    assert len(bus._async_subscribers) == 1
    assert bus._async_subscribers[0][0] is async_cb
    assert bus._async_subscribers[0][1] is None


def test_emit_with_async_subscriber_no_event_loop_does_not_crash():
    """emit must not raise when there is no running event loop."""
    bus = EventBus()

    async def async_cb(e: Event) -> None:
        pass

    bus.subscribe_async(async_cb, event_type=EventType.ACTION_STARTED)
    # No running event loop — RuntimeError is silently swallowed inside emit
    bus.emit(Event(type=EventType.ACTION_STARTED))  # must not raise


# ---------------------------------------------------------------------------
# 21. Event data is accessible
# ---------------------------------------------------------------------------

def test_event_data_accessible():
    payload = {"tool": "bash", "cmd": "ls", "risk": 0.1}
    event = Event(type=EventType.ACTION_STARTED, data=payload)
    assert event.data["tool"] == "bash"
    assert event.data["cmd"] == "ls"
    assert event.data["risk"] == pytest.approx(0.1)


def test_event_default_data_is_empty_dict():
    event = Event(type=EventType.POLICY_DECISION)
    assert event.data == {}
