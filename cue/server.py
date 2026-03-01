"""CUE MCP Server — FastMCP instance with safety initialization."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from cue.safety.guardrails import Guardrails, load_config
from cue.safety.logger import AuditLogger
from cue.utils.screen import enable_dpi_awareness

# Enable DPI awareness before any screen operations
enable_dpi_awareness()

# Load configuration
config = load_config()

# Initialize safety components
guardrails = Guardrails(config)
audit = AuditLogger(path=config.log_path, enabled=config.log_enabled)

# Create FastMCP server
mcp = FastMCP("CUE — Computer Use Engine")

# Import tool modules to register them with the server
import cue.tools.screenshot  # noqa: E402, F401
import cue.tools.mouse  # noqa: E402, F401
import cue.tools.keyboard  # noqa: E402, F401
import cue.tools.window  # noqa: E402, F401
