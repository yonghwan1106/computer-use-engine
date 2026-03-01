"""Safety guardrails: action limits, app allow/block lists, key blocking."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "default.yaml"


class SafetyConfig:
    """Loaded safety configuration from YAML."""

    def __init__(self, data: dict[str, Any]) -> None:
        safety = data.get("safety", {})
        self.max_actions: int = safety.get("max_actions_per_session", 100)
        self.action_delay: float = safety.get("action_delay", 0.05)
        self.failsafe: bool = safety.get("failsafe", True)
        self.allowed_apps: list[str] = [
            a.lower() for a in safety.get("allowed_apps", [])
        ]
        self.blocked_apps: list[str] = [
            a.lower() for a in safety.get("blocked_apps", [])
        ]
        self.blocked_keys: list[str] = [
            k.lower() for k in safety.get("blocked_keys", [])
        ]

        ss = data.get("screenshot", {})
        self.ss_format: str = ss.get("format", "JPEG")
        self.ss_quality: int = ss.get("quality", 80)
        self.ss_max_dimension: int = ss.get("max_dimension", 1568)

        log = data.get("logging", {})
        self.log_enabled: bool = log.get("enabled", True)
        self.log_path: str = log.get("path", "cue_audit.jsonl")
        self.log_level: str = log.get("level", "INFO")


def load_config(path: Optional[Path] = None) -> SafetyConfig:
    """Load safety configuration from a YAML file.

    Falls back to built-in defaults if the file is missing.
    """
    config_path = path or _DEFAULT_CONFIG_PATH
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    return SafetyConfig(data)


class Guardrails:
    """Runtime safety enforcement."""

    def __init__(self, config: Optional[SafetyConfig] = None) -> None:
        self.config = config or load_config()
        self._action_count = 0

    @property
    def action_count(self) -> int:
        return self._action_count

    def check_action_limit(self) -> None:
        """Raise if session action limit is exceeded."""
        if self.config.max_actions > 0 and self._action_count >= self.config.max_actions:
            raise RuntimeError(
                f"Session action limit reached ({self.config.max_actions}). "
                "Reset the session or increase the limit in config."
            )

    def increment_action(self) -> int:
        """Increment and return the current action count."""
        self.check_action_limit()
        self._action_count += 1
        return self._action_count

    def check_app_allowed(self, window_title: str) -> None:
        """Raise if the target app is blocked or not in the allowlist."""
        title_lower = window_title.lower()

        for blocked in self.config.blocked_apps:
            if blocked in title_lower:
                raise PermissionError(
                    f"App '{window_title}' is in the blocked list."
                )

        if self.config.allowed_apps:
            if not any(allowed in title_lower for allowed in self.config.allowed_apps):
                raise PermissionError(
                    f"App '{window_title}' is not in the allowed list."
                )

    def check_key_allowed(self, combo: str) -> None:
        """Raise if the key combination is blocked."""
        normalized = combo.lower().replace(" ", "")
        for blocked in self.config.blocked_keys:
            blocked_normalized = blocked.replace(" ", "")
            if normalized == blocked_normalized:
                raise PermissionError(
                    f"Key combination '{combo}' is blocked by safety config."
                )

    def reset(self) -> None:
        """Reset session action counter."""
        self._action_count = 0
