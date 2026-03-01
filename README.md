# CUE — Computer Use Enforcer

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)

**English** | [한국어](README.ko.md)

> **The missing safety layer between AI agents and your desktop.**

CUE is safety middleware for AI computer use agents. It monitors, enforces policies, and provides guardrails so that AI agents can interact with your desktop — safely and compliantly.

---

## Problem

AI computer use is accelerating fast, but safety infrastructure hasn't kept up:

- **Rapid adoption** — 40% of enterprises plan to deploy AI computer use agents by end of 2026
- **No guardrails** — only 50% of organizations have any safety controls for autonomous agents
- **Regulation is coming** — the EU AI Act (Aug 2026) mandates human oversight for high-risk AI systems

There is no open-source framework that sits between AI agents and the desktop to enforce safety policies. CUE fills that gap.

## What CUE Does

```
┌─────────────────────────────────┐
│  Any AI Agent                   │  Claude, GPT, Agent-S, ...
│  (natural language in/out)      │
└──────────┬──────────────────────┘
           │ MCP protocol (stdio)
┌──────────▼──────────────────────┐
│  CUE — Computer Use Enforcer   │  ← this project
│  ┌────────────────────────────┐ │
│  │ Policy Engine              │ │  risk classification, action filtering
│  │ Guardrails                 │ │  app blocklist, key blocking, rate limits
│  │ Audit Logger               │ │  JSONL compliance trail
│  │ Monitor (coming soon)      │ │  real-time dashboard & event streaming
│  └────────────────────────────┘ │
└──────────┬──────────────────────┘
           │ pyautogui / pygetwindow / pywin32
┌──────────▼──────────────────────┐
│  Desktop OS                     │
└─────────────────────────────────┘
```

### Core Value Proposition

| Capability | Status | Description |
|------------|--------|-------------|
| **Action Guardrails** | Available | App blocklist, key blocking, per-session action limits |
| **Audit Logging** | Available | Every action logged to JSONL for compliance review |
| **FAILSAFE** | Available | Mouse to (0,0) aborts immediately |
| **Policy Engine** | Phase 1 | Risk classification, rule-based action filtering |
| **Real-time Monitor** | Phase 2 | Live dashboard with event streaming |
| **Human-in-the-Loop** | Phase 3 | Approval workflows for high-risk actions |
| **Agent Adapters** | Phase 4 | Agent-agnostic backends (Claude, GPT, open-source) |
| **Compliance Reports** | Phase 5 | Automated audit reports for EU AI Act, SOC 2 |

## Quick Start

### 1. Install

```bash
git clone https://github.com/yonghwan1106/computer-use-engine.git
cd computer-use-engine
pip install -e .
```

### 2. Register with Claude

```bash
python scripts/register.py
```

This automatically adds CUE to both Claude Desktop and Claude Code configurations.

### 3. Restart Claude and go

Restart Claude Desktop or Claude Code. Then just ask:

> "Take a screenshot of my screen"

> "Open Notepad and type 'Hello, CUE!'"

> "Show me all open windows"

## Current Features

### MCP Tools (12)

#### Screenshot & Screen

| Tool | Description | Parameters |
|------|-------------|------------|
| `cue_screenshot` | Capture full screen or a region as JPEG | `region_x`, `region_y`, `region_width`, `region_height` (all optional) |
| `cue_screen_size` | Get screen resolution | — |
| `cue_cursor_position` | Get current cursor coordinates | — |

#### Mouse

| Tool | Description | Parameters |
|------|-------------|------------|
| `cue_click` | Click at coordinates | `x`, `y`, `button` (left/right/middle), `clicks` (1-3) |
| `cue_scroll` | Scroll at position | `x`, `y`, `clicks` (positive=up, negative=down) |
| `cue_move` | Move cursor | `x`, `y` |
| `cue_drag` | Drag from point A to B | `start_x`, `start_y`, `end_x`, `end_y`, `button`, `duration` |

#### Keyboard

| Tool | Description | Parameters |
|------|-------------|------------|
| `cue_type` | Type text (auto clipboard fallback for non-ASCII like Korean/CJK) | `text` |
| `cue_key` | Press key or combo | `key` (e.g. `"enter"`, `"ctrl+c"`, `"alt+tab"`) |

#### Window Management

| Tool | Description | Parameters |
|------|-------------|------------|
| `cue_list_windows` | List all visible windows with geometry | — |
| `cue_focus_window` | Focus a window by partial title match | `title` |
| `cue_window_info` | Get active window info | — |

### Safety Features

| Feature | Description | Default |
|---------|-------------|---------|
| **Action limit** | Max actions per session before requiring reset | 100 |
| **App blocklist** | Prevents interaction with sensitive apps | Registry Editor, Windows Security |
| **Key blocklist** | Blocks dangerous key combos | `win+r`, `ctrl+alt+del` |
| **Audit log** | Every action logged to JSONL file | `cue_audit.jsonl` |
| **FAILSAFE** | Move mouse to (0, 0) to abort immediately | Enabled |
| **Action delay** | Pause between actions for safety | 50ms |

## Safety Policy

All safety settings are configurable in `config/default.yaml`:

```yaml
safety:
  max_actions_per_session: 100
  action_delay: 0.05
  failsafe: true
  allowed_apps: []
  blocked_apps:
    - "Windows Security"
    - "Registry Editor"
    - "Task Manager"
  blocked_keys:
    - "win+r"
    - "alt+f4"
    - "ctrl+alt+del"
```

## Manual Registration

If you prefer to configure manually instead of using `register.py`:

**Claude Desktop** — edit `%APPDATA%/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "cue": {
      "command": "python",
      "args": ["-m", "cue"]
    }
  }
}
```

**Claude Code** — edit `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "cue": {
      "command": "python",
      "args": ["-m", "cue"]
    }
  }
}
```

## Project Structure

```
computer-use-engine/
├── cue/
│   ├── __init__.py            # Package version
│   ├── __main__.py            # python -m cue entry point
│   ├── server.py              # FastMCP server initialization
│   ├── tools/
│   │   ├── screenshot.py      # Screen capture tools (3)
│   │   ├── mouse.py           # Mouse control tools (4)
│   │   ├── keyboard.py        # Keyboard input tools (2)
│   │   └── window.py          # Window management tools (3)
│   ├── safety/
│   │   ├── guardrails.py      # Action limits, app/key blocking
│   │   └── logger.py          # JSONL audit logger
│   ├── core/                  # Policy engine, risk scoring (Phase 1)
│   ├── monitor/               # Real-time dashboard (Phase 2)
│   ├── adapters/              # Agent-agnostic backends (Phase 4)
│   └── utils/
│       ├── screen.py          # DPI awareness, image processing
│       └── keymap.py          # xdotool → pyautogui key mapping
├── config/
│   └── default.yaml           # Safety configuration
├── scripts/
│   └── register.py            # Auto-registration for Claude
├── tests/                     # Unit tests
├── pyproject.toml
├── LICENSE                    # Apache 2.0
└── README.md
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run the server directly (stdio mode)
python -m cue
```

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| **MVP** | MCP server, 12 tools, basic guardrails | Done |
| **Phase 1** | Policy engine, risk classification, session management | Next |
| **Phase 2** | Real-time monitoring dashboard, event streaming | Planned |
| **Phase 3** | Human-in-the-loop approval workflows | Planned |
| **Phase 4** | Agent-agnostic adapters (Claude, GPT, Agent-S) | Planned |
| **Phase 5** | Compliance reports (EU AI Act, SOC 2) | Planned |

## Requirements

- Python 3.11+
- Windows 10/11
- Claude Desktop or Claude Code with MCP support

## Contributing

Contributions are welcome! Please see [LICENSE](LICENSE) for details.

## License

[Apache 2.0](LICENSE)
