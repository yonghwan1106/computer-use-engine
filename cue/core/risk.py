"""CUE risk scoring — classify actions by risk level."""

from __future__ import annotations

from cue.core.models import ActionContext, RiskLevel

# Read-only tools that never modify system state
_READONLY_TOOLS = frozenset({
    "cue_screenshot",
    "cue_screen_size",
    "cue_cursor_position",
    "cue_list_windows",
    "cue_window_info",
})

# System-level key combos that are always critical
_CRITICAL_COMBOS = frozenset({
    "ctrl+alt+del",
    "ctrl+alt+delete",
    "win+r",
    "win+l",
    "win+x",
    "alt+f4",
    "ctrl+shift+esc",
})

# Admin / sensitive applications
_CRITICAL_APPS = frozenset({
    "registry editor",
    "windows security",
    "task manager",
    "command prompt",
    "powershell",
    "regedit",
    "cmd.exe",
    "services",
    "local security policy",
    "group policy",
    "device manager",
    "disk management",
})

# Modifier keys that elevate risk when combined
_MODIFIER_KEYS = frozenset({"ctrl", "alt", "shift", "win", "cmd", "meta", "super"})


class RiskScorer:
    """Score and classify actions into risk tiers.

    Tiers:
        LOW      — read-only tools (screenshot, screen_size, etc.)
        MEDIUM   — mouse clicks/moves/scrolls, plain text input
        HIGH     — key combos with modifiers, window focus changes, drag
        CRITICAL — system key combos, admin app interactions
    """

    def score(self, ctx: ActionContext) -> RiskLevel:
        """Return the risk level for the given action context."""
        if self._is_critical(ctx):
            return RiskLevel.CRITICAL
        if self._is_high(ctx):
            return RiskLevel.HIGH
        if ctx.tool in _READONLY_TOOLS:
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    def _is_critical(self, ctx: ActionContext) -> bool:
        """Check for critical-risk indicators."""
        # Critical key combos
        if ctx.key_combo:
            normalized = ctx.key_combo.lower().replace(" ", "")
            parts = sorted(normalized.split("+"))
            for combo in _CRITICAL_COMBOS:
                if parts == sorted(combo.split("+")):
                    return True

        # Critical target apps
        if ctx.target_app:
            app_lower = ctx.target_app.lower()
            for app in _CRITICAL_APPS:
                if app in app_lower:
                    return True

        return False

    def _is_high(self, ctx: ActionContext) -> bool:
        """Check for high-risk indicators."""
        # Key combos with modifier keys
        if ctx.key_combo:
            parts = ctx.key_combo.lower().replace(" ", "").split("+")
            if len(parts) > 1 and any(p in _MODIFIER_KEYS for p in parts):
                return True

        # Window focus changes
        if ctx.tool == "cue_focus_window":
            return True

        # Drag operations
        if ctx.tool == "cue_drag":
            return True

        return False
