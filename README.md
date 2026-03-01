# CUE — Computer Use Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)

**English** | [한국어](README.ko.md)

CUE is an AI Computer Use agent framework that runs as an **MCP (Model Context Protocol) server**. It gives Claude the ability to see your screen, move the mouse, type on the keyboard, and manage windows — all through natural language.

## Why CUE?

Traditional AI Computer Use requires direct API calls with per-token billing. CUE **inverts the architecture**: instead of your code calling the AI, the AI calls CUE through MCP. This means:

- **No extra API costs** — works with your existing Claude Max subscription
- **Natural language control** — just tell Claude what to do on your desktop
- **Safe by default** — action limits, app blocklists, key blocking, and audit logging

```
┌─────────────────────────────┐
│  Claude Desktop / Code      │  ← AI brain (your Max subscription)
│  (natural language in/out)  │
└──────────┬──────────────────┘
           │ MCP protocol (stdio)
┌──────────▼──────────────────┐
│  CUE MCP Server (Python)    │  ← this project
│  12 tools for desktop ctrl  │
└──────────┬──────────────────┘
           │ pyautogui / pygetwindow / pywin32
┌──────────▼──────────────────┐
│  Windows Desktop            │
└─────────────────────────────┘
```

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

## MCP Tools (12)

### Screenshot & Screen

| Tool | Description | Parameters |
|------|-------------|------------|
| `cue_screenshot` | Capture full screen or a region as JPEG | `region_x`, `region_y`, `region_width`, `region_height` (all optional) |
| `cue_screen_size` | Get screen resolution | — |
| `cue_cursor_position` | Get current cursor coordinates | — |

### Mouse

| Tool | Description | Parameters |
|------|-------------|------------|
| `cue_click` | Click at coordinates | `x`, `y`, `button` (left/right/middle), `clicks` (1-3) |
| `cue_scroll` | Scroll at position | `x`, `y`, `clicks` (positive=up, negative=down) |
| `cue_move` | Move cursor | `x`, `y` |
| `cue_drag` | Drag from point A to B | `start_x`, `start_y`, `end_x`, `end_y`, `button`, `duration` |

### Keyboard

| Tool | Description | Parameters |
|------|-------------|------------|
| `cue_type` | Type text (auto clipboard fallback for non-ASCII like Korean/CJK) | `text` |
| `cue_key` | Press key or combo | `key` (e.g. `"enter"`, `"ctrl+c"`, `"alt+tab"`) |

### Window Management

| Tool | Description | Parameters |
|------|-------------|------------|
| `cue_list_windows` | List all visible windows with geometry | — |
| `cue_focus_window` | Focus a window by partial title match | `title` |
| `cue_window_info` | Get active window info | — |

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

## Safety

CUE is designed with safety as a first-class concern:

| Feature | Description | Default |
|---------|-------------|---------|
| **Action limit** | Max actions per session before requiring reset | 100 |
| **App blocklist** | Prevents interaction with sensitive apps | Registry Editor, Windows Security |
| **Key blocklist** | Blocks dangerous key combos | `win+r`, `ctrl+alt+del` |
| **Audit log** | Every action logged to JSONL file | `cue_audit.jsonl` |
| **FAILSAFE** | Move mouse to (0, 0) to abort immediately | Enabled |
| **Action delay** | Pause between actions for safety | 50ms |

All safety settings are configurable in `config/default.yaml`.

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
│   └── utils/
│       ├── screen.py          # DPI awareness, image processing
│       └── keymap.py          # xdotool → pyautogui key mapping
├── config/
│   └── default.yaml           # Safety configuration
├── scripts/
│   └── register.py            # Auto-registration for Claude
├── tests/                     # Unit tests (41 tests)
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

## Key Design Decisions

- **Individual tools over unified action** — MCP works better when Claude can see separate tool schemas rather than a single tool with an `action` parameter
- **JPEG screenshots at quality 80** — 63% smaller than PNG, optimized for Claude's vision (max 1568px longest side)
- **Clipboard fallback for non-ASCII** — `pyautogui.write()` only supports ASCII; CUE auto-detects non-ASCII text and uses `pyperclip.copy()` + `ctrl+v`
- **DPI awareness** — `SetProcessDpiAwareness(2)` called at startup to prevent coordinate mismatch on scaled displays

## Requirements

- Python 3.11+
- Windows 10/11
- Claude Desktop or Claude Code with MCP support

### Dependencies

| Package | Purpose |
|---------|---------|
| `mcp` | FastMCP server framework |
| `pyautogui` | Mouse, keyboard, screenshot |
| `Pillow` | Image processing and JPEG conversion |
| `pywin32` | Windows API access |
| `pygetwindow` | Window enumeration and management |
| `pyperclip` | Clipboard access (non-ASCII input) |
| `pyyaml` | Safety config parsing |

## Roadmap

- [ ] **Phase 2**: YAML workflow engine, CLI (`typer`), recipe system, screenshot diff detection
- [ ] **Phase 3**: Live monitoring, OCR text search (`cue_find_text`), session recording/replay
- [ ] **Phase 4**: Next.js dashboard, community recipe hub, multi-monitor support

## License

[Apache 2.0](LICENSE)
