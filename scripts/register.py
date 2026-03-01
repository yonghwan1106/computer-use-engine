"""Auto-register CUE MCP server in Claude Desktop and Claude Code settings."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def _find_python() -> str:
    """Return the path to the current Python executable."""
    return sys.executable.replace("\\", "/")


def _cue_server_config() -> dict:
    """Build the MCP server config entry for CUE."""
    return {
        "command": _find_python(),
        "args": ["-m", "cue"],
    }


def register_claude_desktop() -> bool:
    """Register CUE in Claude Desktop's claude_desktop_config.json."""
    config_path = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"

    if not config_path.parent.exists():
        print(f"Claude Desktop config directory not found: {config_path.parent}")
        return False

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    data.setdefault("mcpServers", {})
    data["mcpServers"]["cue"] = _cue_server_config()

    # H6: backup existing config before overwriting
    if config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        shutil.copy2(config_path, backup_path)
        print(f"  Backup created: {backup_path}")

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Registered CUE in Claude Desktop: {config_path}")
    return True


def register_claude_code() -> bool:
    """Register CUE in Claude Code's settings.json."""
    config_path = Path.home() / ".claude" / "settings.json"

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}

    data.setdefault("mcpServers", {})
    data["mcpServers"]["cue"] = _cue_server_config()

    # H6: backup existing config before overwriting
    if config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        shutil.copy2(config_path, backup_path)
        print(f"  Backup created: {backup_path}")

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Registered CUE in Claude Code: {config_path}")
    return True


def main():
    print("CUE MCP Server Registration")
    print("=" * 40)
    print()

    desktop_ok = register_claude_desktop()
    code_ok = register_claude_code()

    print()
    if desktop_ok or code_ok:
        print("Registration complete. Restart Claude Desktop/Code to activate.")
    else:
        print("No Claude configurations found. Please install Claude Desktop or Claude Code first.")


if __name__ == "__main__":
    main()
