"""Non-blocking keyboard input thread (Windows msvcrt)."""

import time
import msvcrt
from dataclasses import dataclass

from .modes import MODE_KEYS


@dataclass
class InputState:
    paused:        bool = False
    quit:          bool = False
    mode_name:     str = "custom"
    charset_idx:   int  = 0
    detail_idx:    int  = 0
    auto_detail:   bool = False
    colorized:     bool = False
    theme_idx:     int  = 0
    hud_visible:   bool = True
    fullscreen:    bool = False
    pause_toggle:  bool = False   # set True when pause flips; core reacts then clears
    fullscreen_toggle: bool = False
    hud_toggle:    bool = False
    mode_changed:  bool = False
    redraw:        bool = False
    charset_count: int  = 5
    detail_count:  int  = 1
    theme_count:   int  = 1


def input_loop(state: InputState) -> None:
    """Run in a daemon thread; mutates *state* in response to keypresses."""
    while not state.quit:
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch in (b"\xe0", b"\x00"):        # arrow / fn key prefix
                msvcrt.getch()                  # discard the second byte
            elif ch in (b" ", b"p", b"P"):
                state.paused       = not state.paused
                state.pause_toggle = True
            elif ch in (b"v", b"V"):
                state.charset_idx = (state.charset_idx + 1) % state.charset_count
                state.mode_name = "custom"
                state.redraw = True
            elif ch in (b"m", b"M"):
                state.detail_idx = (state.detail_idx + 1) % state.detail_count
                state.mode_name = "custom"
                state.redraw = True
            elif ch in (b"a", b"A"):
                state.auto_detail = not state.auto_detail
                state.mode_name = "custom"
                state.redraw = True
            elif ch in (b"c", b"C"):
                state.colorized = not state.colorized
                state.mode_name = "custom"
                state.redraw = True
            elif ch in (b"t", b"T"):
                state.theme_idx = (state.theme_idx + 1) % state.theme_count
                state.mode_name = "custom"
                state.redraw = True
            elif ch in MODE_KEYS:
                state.mode_name = MODE_KEYS[ch]
                state.mode_changed = True
                state.redraw = True
            elif ch in (b"f", b"F"):
                state.fullscreen = not state.fullscreen
                state.hud_visible = not state.fullscreen
                state.fullscreen_toggle = True
                state.redraw = True
            elif ch in (b"h", b"H"):
                state.hud_visible = not state.hud_visible
                if state.hud_visible:
                    state.fullscreen = False
                state.hud_toggle = True
                state.redraw = True
            elif ch in (b"q", b"Q", b"\x1b"):
                state.quit = True
        time.sleep(0.01)
