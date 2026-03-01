"""Human-in-the-loop approval workflow for HOLD policy decisions."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ApprovalStatus(Enum):
    """Lifecycle state of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """A pending request for human approval."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    tool: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    target_app: Optional[str] = None
    key_combo: Optional[str] = None
    reason: str = ""
    rule_name: str = ""
    risk_level: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolution_reason: Optional[str] = None


@dataclass
class ApprovalGrant:
    """One-time grant allowing a previously held action to proceed."""

    request_id: str = ""
    tool: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    target_app: Optional[str] = None
    key_combo: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    consumed: bool = False


class ApprovalManager:
    """Manages approval requests and one-time grants for HOLD decisions.

    Design decisions:
    - Lazy expiration: stale requests are expired on access, no background thread.
    - One-time grants: consumed on first matching check_grant call.
    - Grant TTL: approved grants expire after grant_ttl seconds.
    """

    def __init__(self, timeout: float = 300.0, grant_ttl: float = 60.0) -> None:
        self.timeout = timeout
        self.grant_ttl = grant_ttl
        self._requests: dict[str, ApprovalRequest] = {}
        self._grants: list[ApprovalGrant] = []

    def create_request(
        self,
        tool: str,
        params: dict[str, Any] | None = None,
        reason: str = "",
        rule_name: str = "",
        risk_level: str = "",
        target_app: str | None = None,
        key_combo: str | None = None,
    ) -> ApprovalRequest:
        """Create a new approval request for a HOLD decision."""
        request = ApprovalRequest(
            tool=tool,
            params=params or {},
            target_app=target_app,
            key_combo=key_combo,
            reason=reason,
            rule_name=rule_name,
            risk_level=risk_level,
        )
        self._requests[request.id] = request
        return request

    def approve(self, request_id: str, reason: str | None = None) -> ApprovalGrant:
        """Approve a pending request and create a one-time grant.

        Raises:
            KeyError: If request_id is not found.
            ValueError: If the request is not in PENDING status.
        """
        self._expire_stale()
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"Approval request '{request_id}' not found.")
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Request '{request_id}' is {request.status.value}, not pending."
            )

        now = time.time()
        request.status = ApprovalStatus.APPROVED
        request.resolved_at = now
        request.resolution_reason = reason

        grant = ApprovalGrant(
            request_id=request_id,
            tool=request.tool,
            params=dict(request.params),
            target_app=request.target_app,
            key_combo=request.key_combo,
            created_at=now,
            expires_at=now + self.grant_ttl,
        )
        self._grants.append(grant)
        return grant

    def deny(self, request_id: str, reason: str | None = None) -> None:
        """Deny a pending request.

        Raises:
            KeyError: If request_id is not found.
            ValueError: If the request is not in PENDING status.
        """
        self._expire_stale()
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"Approval request '{request_id}' not found.")
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Request '{request_id}' is {request.status.value}, not pending."
            )

        request.status = ApprovalStatus.DENIED
        request.resolved_at = time.time()
        request.resolution_reason = reason

    def get_pending(self) -> list[ApprovalRequest]:
        """Return all pending requests, expiring stale ones first."""
        self._expire_stale()
        return [
            r for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING
        ]

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Return a request by ID, or None if not found."""
        return self._requests.get(request_id)

    def check_grant(
        self,
        tool: str,
        params: dict[str, Any] | None = None,
        target_app: str | None = None,
        key_combo: str | None = None,
    ) -> ApprovalGrant | None:
        """Find and consume a matching, unexpired grant.

        Returns the consumed grant, or None if no match is found.
        """
        now = time.time()
        for grant in self._grants:
            if grant.consumed:
                continue
            if now >= grant.expires_at:
                continue
            if grant.tool != tool:
                continue
            # Match found — consume and return
            grant.consumed = True
            return grant
        return None

    def _expire_stale(self) -> None:
        """Expire pending requests that have exceeded the timeout."""
        now = time.time()
        for request in self._requests.values():
            if request.status != ApprovalStatus.PENDING:
                continue
            if now - request.created_at >= self.timeout:
                request.status = ApprovalStatus.EXPIRED
                request.resolved_at = now
