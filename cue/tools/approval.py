"""Approval tools: human-in-the-loop approval workflow for HOLD decisions."""

from __future__ import annotations

from typing import Any, Optional

import cue.server as _server
from cue.server import mcp


@mcp.tool()
def cue_pending_approvals() -> list[dict[str, Any]]:
    """List all pending approval requests.

    Returns:
        List of pending approval requests with id, tool, reason, and age.
    """
    if _server.approval_manager is None:
        return []

    pending = _server.approval_manager.get_pending()
    import time

    now = time.time()
    return [
        {
            "id": r.id,
            "tool": r.tool,
            "params": r.params,
            "target_app": r.target_app,
            "key_combo": r.key_combo,
            "reason": r.reason,
            "rule_name": r.rule_name,
            "risk_level": r.risk_level,
            "age_seconds": round(now - r.created_at, 1),
        }
        for r in pending
    ]


@mcp.tool()
def cue_approve_action(
    request_id: str,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    """Approve a pending action request, granting a time-limited permit to retry.

    Args:
        request_id: The approval request ID to approve.
        reason: Optional reason for the approval.

    Returns:
        Confirmation with grant details and expiry time.
    """
    if _server.approval_manager is None:
        return {"error": "Approval system not initialized."}

    from cue.monitor.events import Event, EventType

    try:
        grant = _server.approval_manager.approve(request_id, reason)
    except (KeyError, ValueError) as exc:
        return {"error": str(exc)}

    if _server.event_bus is not None:
        _server.event_bus.emit(Event(
            type=EventType.APPROVAL_GRANTED,
            data={
                "request_id": request_id,
                "tool": grant.tool,
                "reason": reason or "",
                "expires_at": grant.expires_at,
            },
        ))

    return {
        "status": "approved",
        "request_id": request_id,
        "tool": grant.tool,
        "grant_ttl_seconds": _server.approval_manager.grant_ttl,
        "message": f"Approved. Grant valid for {_server.approval_manager.grant_ttl:.0f} seconds.",
    }


@mcp.tool()
def cue_deny_action(
    request_id: str,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    """Deny a pending action request.

    Args:
        request_id: The approval request ID to deny.
        reason: Optional reason for the denial.

    Returns:
        Confirmation of denial.
    """
    if _server.approval_manager is None:
        return {"error": "Approval system not initialized."}

    from cue.monitor.events import Event, EventType

    try:
        _server.approval_manager.deny(request_id, reason)
    except (KeyError, ValueError) as exc:
        return {"error": str(exc)}

    if _server.event_bus is not None:
        _server.event_bus.emit(Event(
            type=EventType.APPROVAL_DENIED,
            data={
                "request_id": request_id,
                "reason": reason or "",
            },
        ))

    return {
        "status": "denied",
        "request_id": request_id,
        "message": "Action denied.",
    }
