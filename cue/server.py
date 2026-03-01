"""CUE — Computer Use Enforcer: MCP server with safety enforcement."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from cue.safety.guardrails import Guardrails, SafetyConfig, load_config
from cue.safety.logger import AuditLogger
from cue.utils.screen import enable_dpi_awareness

# Create FastMCP server (no side effects)
mcp = FastMCP("CUE — Computer Use Enforcer")

# Lazy-init holders (populated by init())
config: SafetyConfig | None = None
guardrails: Guardrails | None = None
audit: AuditLogger | None = None
_initialized = False


def init() -> None:
    """Initialize safety components. Called once before the server starts."""
    global config, guardrails, audit, _initialized
    if _initialized:
        return

    import pyautogui

    enable_dpi_awareness()
    config = load_config()
    pyautogui.FAILSAFE = config.failsafe  # C1: apply failsafe setting
    guardrails = Guardrails(config)
    audit = AuditLogger(path=config.log_path, enabled=config.log_enabled)
    _initialized = True


# Import tool modules to register them with the server
import cue.tools.screenshot  # noqa: E402, F401
import cue.tools.mouse  # noqa: E402, F401
import cue.tools.keyboard  # noqa: E402, F401
import cue.tools.window  # noqa: E402, F401
