"""Monitoring tools: session status, recent events, safety summary."""

from __future__ import annotations

from typing import Any, Optional

import cue.server as _server
from cue.server import mcp


@mcp.tool()
def cue_session_status() -> dict[str, Any]:
    """Get current session status, action count, and risk distribution.

    Returns:
        Dictionary with session info, action count, and risk breakdown.
    """
    if _server.guardrails is None or _server.guardrails._session_manager is None:
        return {"error": "Safety system not initialized."}

    sm = _server.guardrails._session_manager
    session = sm.current_session
    if session is None:
        return {"status": "no_session", "action_count": 0}

    return session.summary()


@mcp.tool()
def cue_recent_events(
    count: int = 50,
    event_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Get recent events from the event buffer.

    Args:
        count: Maximum number of events to return (default 50).
        event_type: Filter by event type name (e.g. "action_completed").
    """
    if _server.event_bus is None:
        return []

    from cue.monitor.events import EventType

    et_filter = None
    if event_type is not None:
        try:
            et_filter = EventType(event_type)
        except ValueError:
            return [{"error": f"Unknown event type: {event_type}"}]

    events = _server.event_bus.get_buffered(event_type=et_filter)
    # Return most recent `count` events, newest first
    recent = events[-count:] if len(events) > count else events
    return [
        {
            "id": e.id,
            "type": e.type.value,
            "timestamp": e.timestamp,
            "data": e.data,
        }
        for e in reversed(recent)
    ]


@mcp.tool()
def cue_safety_summary() -> dict[str, Any]:
    """Get a comprehensive safety summary.

    Returns overall denied count, alert count, recent denials,
    and session information.
    """
    if _server.event_bus is None:
        return {"error": "Event system not initialized."}

    from cue.monitor.events import EventType

    all_events = _server.event_bus.get_buffered()
    denied = [e for e in all_events if e.type == EventType.ACTION_DENIED]
    alerts = [e for e in all_events if e.type == EventType.RISK_ALERT]

    recent_denials = [
        {
            "tool": e.data.get("tool", ""),
            "rule_name": e.data.get("rule_name", ""),
            "reason": e.data.get("reason", ""),
            "timestamp": e.timestamp,
        }
        for e in denied[-10:]  # Last 10 denials
    ]

    # Session info
    session_info = {"status": "no_session", "action_count": 0}
    if _server.guardrails and _server.guardrails._session_manager:
        sm = _server.guardrails._session_manager
        session = sm.current_session
        if session is not None:
            session_info = session.summary()

    return {
        "denied_count": len(denied),
        "alert_count": len(alerts),
        "total_events": len(all_events),
        "recent_denials": recent_denials,
        "session": session_info,
    }
