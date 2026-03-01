"""CUE event bus — real-time event streaming for the monitoring dashboard."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class EventType(Enum):
    """Types of events emitted by the CUE safety system."""

    ACTION_STARTED = "action_started"
    ACTION_COMPLETED = "action_completed"
    ACTION_DENIED = "action_denied"
    POLICY_DECISION = "policy_decision"
    RISK_ALERT = "risk_alert"
    SESSION_STARTED = "session_started"
    SESSION_PAUSED = "session_paused"
    SESSION_RESUMED = "session_resumed"
    SESSION_TERMINATED = "session_terminated"
    GUARDRAIL_TRIGGERED = "guardrail_triggered"


@dataclass(frozen=True)
class Event:
    """Immutable event record."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Publish-subscribe event bus for CUE monitoring.

    Supports sync and async subscribers with bounded event buffering
    for dashboard reconnection.
    """

    def __init__(self, buffer_size: int = 1000) -> None:
        self._sync_subscribers: list[tuple[Callable, Optional[EventType]]] = []
        self._async_subscribers: list[tuple[Callable, Optional[EventType]]] = []
        self._buffer: deque[Event] = deque(maxlen=buffer_size)

    def subscribe(
        self, callback: Callable, event_type: Optional[EventType] = None
    ) -> None:
        """Register a synchronous subscriber.

        Args:
            callback: Function to call with each matching Event.
            event_type: If set, only receive events of this type.
        """
        self._sync_subscribers.append((callback, event_type))

    def subscribe_async(
        self, callback: Callable, event_type: Optional[EventType] = None
    ) -> None:
        """Register an async subscriber.

        Args:
            callback: Async function to call with each matching Event.
            event_type: If set, only receive events of this type.
        """
        self._async_subscribers.append((callback, event_type))

    def unsubscribe(self, callback: Callable) -> None:
        """Remove a subscriber (sync or async)."""
        self._sync_subscribers = [
            (cb, et) for cb, et in self._sync_subscribers if cb is not callback
        ]
        self._async_subscribers = [
            (cb, et) for cb, et in self._async_subscribers if cb is not callback
        ]

    def emit(self, event: Event) -> None:
        """Emit an event to all matching subscribers and buffer it."""
        self._buffer.append(event)

        # Notify sync subscribers
        for callback, event_type in self._sync_subscribers:
            if event_type is not None and event.type != event_type:
                continue
            try:
                callback(event)
            except Exception:
                pass  # Never let a subscriber crash the pipeline

        # Notify async subscribers
        for callback, event_type in self._async_subscribers:
            if event_type is not None and event.type != event_type:
                continue
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(callback(event))
            except RuntimeError:
                pass  # No running event loop — skip async subscriber

    def get_buffered(
        self,
        since: Optional[float] = None,
        event_type: Optional[EventType] = None,
    ) -> list[Event]:
        """Return buffered events, optionally filtered by timestamp and type."""
        result = []
        for event in self._buffer:
            if since is not None and event.timestamp < since:
                continue
            if event_type is not None and event.type != event_type:
                continue
            result.append(event)
        return result

    def clear_buffer(self) -> None:
        """Clear the event buffer."""
        self._buffer.clear()
