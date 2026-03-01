"""Tests for keyboard tools."""

from __future__ import annotations

from cue.utils.keymap import map_key, parse_hotkey


class TestMapKey:
    def test_xdotool_mapping(self):
        assert map_key("Return") == "enter"
        assert map_key("super") == "win"
        assert map_key("Escape") == "esc"

    def test_passthrough(self):
        assert map_key("a") == "a"
        assert map_key("f5") == "f5"

    def test_case_insensitive(self):
        assert map_key("RETURN") == "enter"
        assert map_key("Super") == "win"


class TestParseHotkey:
    def test_single_key(self):
        assert parse_hotkey("enter") == ["enter"]

    def test_ctrl_c(self):
        result = parse_hotkey("ctrl+c")
        assert result == ["ctrl", "c"]

    def test_ctrl_shift_s(self):
        result = parse_hotkey("ctrl+shift+s")
        assert result == ["ctrl", "shift", "s"]

    def test_modifier_aliases(self):
        result = parse_hotkey("command+a")
        assert result == ["win", "a"]

    def test_meta_alias(self):
        result = parse_hotkey("meta+l")
        assert result == ["win", "l"]
