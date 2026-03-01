"""Key mapping: xdotool-style key names to pyautogui key names."""

from __future__ import annotations

# xdotool / Anthropic computer-use key names → pyautogui equivalents
XDOTOOL_TO_PYAUTOGUI: dict[str, str] = {
    # Modifiers
    "super": "win",
    "super_l": "winleft",
    "super_r": "winright",
    "control_l": "ctrlleft",
    "control_r": "ctrlright",
    "alt_l": "altleft",
    "alt_r": "altright",
    "shift_l": "shiftleft",
    "shift_r": "shiftright",
    # Navigation
    "return": "enter",
    "escape": "esc",
    "prior": "pageup",
    "next": "pagedown",
    "backspace": "backspace",
    "delete": "delete",
    "home": "home",
    "end": "end",
    "insert": "insert",
    # Arrow keys
    "left": "left",
    "right": "right",
    "up": "up",
    "down": "down",
    # Function keys
    "f1": "f1",
    "f2": "f2",
    "f3": "f3",
    "f4": "f4",
    "f5": "f5",
    "f6": "f6",
    "f7": "f7",
    "f8": "f8",
    "f9": "f9",
    "f10": "f10",
    "f11": "f11",
    "f12": "f12",
    # Whitespace
    "tab": "tab",
    "space": "space",
    # Misc
    "caps_lock": "capslock",
    "num_lock": "numlock",
    "scroll_lock": "scrolllock",
    "print": "printscreen",
    "menu": "apps",
}

# Common modifier aliases used in combo strings (e.g. "ctrl+c")
MODIFIER_ALIASES: dict[str, str] = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "win": "win",
    "super": "win",
    "cmd": "win",
    "command": "win",
    "meta": "win",
}


def map_key(key: str) -> str:
    """Map a single key name to pyautogui format.

    Tries xdotool mapping first, then returns the key as-is
    (pyautogui accepts many names directly).
    """
    lower = key.lower().strip()
    return XDOTOOL_TO_PYAUTOGUI.get(lower, lower)


def parse_hotkey(combo: str) -> list[str]:
    """Parse a hotkey combo string like 'ctrl+shift+a' into a list of pyautogui keys.

    Handles '+' as separator. Each part is mapped through map_key.
    """
    parts = [p.strip() for p in combo.lower().split("+") if p.strip()]
    mapped: list[str] = []
    for part in parts:
        alias = MODIFIER_ALIASES.get(part)
        if alias:
            mapped.append(alias)
        else:
            mapped.append(map_key(part))
    return mapped
