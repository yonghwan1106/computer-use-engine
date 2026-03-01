"""CUE — Computer Use Enforcer: MCP server with safety enforcement."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from cue.monitor.events import EventBus
from cue.safety.guardrails import Guardrails, SafetyConfig, load_config
from cue.safety.logger import AuditLogger
from cue.safety.pipeline import SafetyPipeline
from cue.utils.screen import enable_dpi_awareness

# Create FastMCP server (no side effects)
mcp = FastMCP("CUE — Computer Use Enforcer")

# Lazy-init holders (populated by init())
config: SafetyConfig | None = None
guardrails: Guardrails | None = None
audit: AuditLogger | None = None
event_bus: EventBus | None = None
pipeline: SafetyPipeline | None = None
approval_manager: object | None = None
_initialized = False


def init() -> None:
    """Initialize safety components. Called once before the server starts."""
    global config, guardrails, audit, event_bus, pipeline, approval_manager, _initialized
    if _initialized:
        return

    import pyautogui

    from cue.core.policy import PolicyEngine
    from cue.core.risk import RiskScorer
    from cue.core.session import SessionManager

    enable_dpi_awareness()
    config = load_config()
    pyautogui.FAILSAFE = config.failsafe  # C1: apply failsafe setting
    guardrails = Guardrails(config)
    audit = AuditLogger(path=config.log_path, enabled=config.log_enabled)

    # Phase 1: attach policy engine and session manager
    risk_scorer = RiskScorer()
    policy_engine = PolicyEngine.from_config(config.policies, risk_scorer)
    session_manager = SessionManager(max_actions=config.max_actions)
    guardrails.attach_policy_engine(policy_engine)
    guardrails.attach_session_manager(session_manager)

    # Phase 2: event bus and safety pipeline
    event_bus = EventBus(buffer_size=config.event_buffer_size)
    session_manager.event_bus = event_bus

    # Phase 3: approval manager for HOLD decisions
    from cue.core.approval import ApprovalManager

    approval_manager = ApprovalManager(
        timeout=config.approval_timeout,
        grant_ttl=config.approval_grant_ttl,
    )
    pipeline = SafetyPipeline(
        policy_engine, session_manager, event_bus, audit,
        approval_manager=approval_manager,
    )

    _initialized = True


# Import tool modules to register them with the server
import cue.tools.screenshot  # noqa: E402, F401
import cue.tools.mouse  # noqa: E402, F401
import cue.tools.keyboard  # noqa: E402, F401
import cue.tools.window  # noqa: E402, F401
import cue.tools.monitor  # noqa: E402, F401
import cue.tools.approval  # noqa: E402, F401
