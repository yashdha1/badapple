"""Windows console helpers: freeze size and disable manual resize while playing."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


class ConsoleWindowLock:
    """Best-effort lock for console window size and resize controls."""

    MF_BYCOMMAND = 0x00000000
    MF_ENABLED = 0x00000000
    MF_GRAYED = 0x00000001
    SC_SIZE = 0xF000
    SC_MAXIMIZE = 0xF030

    SW_MAXIMIZE = 3
    SW_RESTORE = 9

    def __init__(self) -> None:
        self._enabled = os.name == "nt"
        self._locked = False
        self._saved_cols = 120
        self._saved_rows = 40

        if not self._enabled:
            self._user32 = None
            self._kernel32 = None
            self._hwnd = 0
            return

        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        self._kernel32.GetConsoleWindow.restype = wintypes.HWND
        self._user32.GetSystemMenu.argtypes = [wintypes.HWND, wintypes.BOOL]
        self._user32.GetSystemMenu.restype = wintypes.HMENU
        self._user32.EnableMenuItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
        self._user32.EnableMenuItem.restype = wintypes.BOOL
        self._user32.DrawMenuBar.argtypes = [wintypes.HWND]
        self._user32.DrawMenuBar.restype = wintypes.BOOL
        self._user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self._user32.ShowWindow.restype = wintypes.BOOL

        self._hwnd = self._kernel32.GetConsoleWindow()

    def _mode_con(self, cols: int, rows: int) -> None:
        os.system(f"mode con: cols={max(cols, 40)} lines={max(rows, 20)} >nul")

    def _set_resize_enabled(self, enabled: bool) -> None:
        if not self._enabled or not self._hwnd:
            return
        menu = self._user32.GetSystemMenu(self._hwnd, False)
        if not menu:
            return

        flag = self.MF_BYCOMMAND | (self.MF_ENABLED if enabled else self.MF_GRAYED)
        self._user32.EnableMenuItem(menu, self.SC_SIZE, flag)
        self._user32.EnableMenuItem(menu, self.SC_MAXIMIZE, flag)
        self._user32.DrawMenuBar(self._hwnd)

    def acquire(self, cols: int, rows: int) -> None:
        """Freeze current playback size and disable manual resize controls."""
        if self._locked:
            return

        try:
            sz = os.get_terminal_size()
            self._saved_cols, self._saved_rows = sz.columns, sz.lines
        except OSError:
            pass

        self._mode_con(cols, rows)
        self._set_resize_enabled(False)
        self._locked = True

    def set_maximized(self, maximized: bool) -> None:
        """Toggle maximize/restore window state (best effort)."""
        if not self._enabled or not self._hwnd:
            return
        self._user32.ShowWindow(self._hwnd, self.SW_MAXIMIZE if maximized else self.SW_RESTORE)

    def release(self) -> None:
        """Restore prior resize behavior and the original console dimensions."""
        if not self._locked:
            return

        self._set_resize_enabled(True)
        self._mode_con(self._saved_cols, self._saved_rows)
        self._locked = False
