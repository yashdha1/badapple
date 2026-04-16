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
        "restore_mode": True,   # restore terminal to pre-playback font/size
    },
    "high": {
        "label": "HighDef",
        "charset_idx": 26,      # Braille Sweep — cinematic high quality
        "detail_idx": 3,        # Hyper
        "auto_detail": True,
        "colorized": True,
        "theme_idx": 3,
        "hd_mode": True,        # triggers terminal maximize + font shrink to 8 px
    },
    "ultra": {
        "label": "Ultra",
        "charset_idx": 0,       # Detailed — 70+ characters, finest brightness mapping
        "detail_idx": 3,        # Hyper
        "auto_detail": True,
        "colorized": True,      # per-pixel ANSI-256 color from original frame
        "theme_idx": 3,
        "fps_cap": 0.0,         # uncapped display; RLE + faster resize are the main limiters
        "pixel_mode": True,     # triggers terminal resize + per-pixel color
    },
}

MODE_KEYS = {
    b"1": "chill",
    b"2": "high",
    b"3": "ultra",
}
