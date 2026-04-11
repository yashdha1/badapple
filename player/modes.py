"""Playback mode presets for user-friendly auto configuration."""

from __future__ import annotations

MODE_PRESETS: dict[str, dict[str, object]] = {
    "chill": {
        "label": "Chill",
        "charset_idx": 1,
        "detail_idx": 0,
        "auto_detail": False,
        "colorized": False,
        "theme_idx": 0,
    },
    "high": {
        "label": "High",
        "charset_idx": 10,
        "detail_idx": 2,
        "auto_detail": True,
        "colorized": True,
        "theme_idx": 2,
    },
    "ultra": {
        "label": "Ultra",
        "charset_idx": 26,
        "detail_idx": 3,
        "auto_detail": True,
        "colorized": True,
        "theme_idx": 3,
    },
}

MODE_KEYS = {
    b"1": "chill",
    b"2": "high",
    b"3": "ultra",
}
