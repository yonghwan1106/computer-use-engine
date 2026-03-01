"""CUE adapter base — protocol for agent-agnostic computer use backends."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ComputerUseAdapter(Protocol):
    """Protocol for agent-agnostic computer use backends.

    TODO (Phase 4):
        - Define standard action interface (click, type, screenshot, etc.)
        - Implement adapters for Claude, GPT, Agent-S
        - Support adapter discovery and registration
        - Normalize action parameters across agent APIs
    """

    pass
