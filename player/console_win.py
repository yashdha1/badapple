"""Windows console helpers: freeze size and disable manual resize while playing."""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
import time as _time

# Windows Terminal sets this for panes hosted inside wt.exe (not classic conhost.exe).
_IN_WINDOWS_TERMINAL = bool(os.environ.get("WT_SESSION") or os.environ.get("WT_PROFILE_ID"))


# ── Win32 font-info structure ─────────────────────────────────────────────────
_LF_FACESIZE = 32


class _COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]


class _CONSOLE_FONT_INFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize",     ctypes.c_ulong),
        ("nFont",      ctypes.c_ulong),
        ("dwFontSize", _COORD),
        ("FontFamily", ctypes.c_uint),
        ("FontWeight", ctypes.c_uint),
        ("FaceName",   ctypes.c_wchar * _LF_FACESIZE),
    ]


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", ctypes.c_uint),
    ]


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
        self._user32.MonitorFromWindow.argtypes = [wintypes.HWND, ctypes.c_uint]
        self._user32.MonitorFromWindow.restype = wintypes.HMONITOR
        self._user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(_MONITORINFO)]
        self._user32.GetMonitorInfoW.restype = wintypes.BOOL
        self._user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        self._user32.SetWindowPos.restype = wintypes.BOOL
        self._user32.GetParent.argtypes = [wintypes.HWND]
        self._user32.GetParent.restype = wintypes.HWND
        self._user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
        self._user32.GetAncestor.restype = wintypes.HWND
        self._user32.PostMessageW.argtypes = [
            wintypes.HWND,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_long,
        ]
        self._user32.PostMessageW.restype = wintypes.BOOL
        self._user32.BringWindowToTop.argtypes = [wintypes.HWND]
        self._user32.BringWindowToTop.restype = wintypes.BOOL

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
        if not self._enabled:
            return
        host = self._host_hwnd_for_resize() or self._hwnd
        if not host:
            return
        self._user32.ShowWindow(host, self.SW_MAXIMIZE if maximized else self.SW_RESTORE)

    def _host_hwnd_for_resize(self) -> int:
        """
        ``GetConsoleWindow()`` under Windows Terminal / ConPTY is usually a *child*
        HWND. Resizing it does nothing visible; walk ``GetParent`` to the real
        top-level frame (the one users resize in pwsh/WT).
        """
        if not self._enabled:
            return 0
        cur = self._kernel32.GetConsoleWindow()
        if not cur:
            return 0
        for _ in range(48):
            parent = self._user32.GetParent(cur)
            if not parent:
                break
            cur = parent
        return cur

    def _primary_work_area_pixels(self) -> tuple[int, int] | None:
        """Fallback when ``GetConsoleWindow`` is 0: full primary monitor work area."""
        SPI_GETWORKAREA = 0x0030
        try:
            r = _RECT()
            if self._user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0):
                return int(r.right - r.left), int(r.bottom - r.top)
        except Exception:
            pass
        return None

    def _vt_resize_window_pixels(self, width_px: int, height_px: int) -> None:
        """
        XTerm-style: CSI 8 ; height ; width t — resize window in *pixels* (order matters).
        Windows Terminal often honors this for the active pane.
        """
        try:
            h = max(120, int(height_px))
            w = max(200, int(width_px))
            sys.stdout.write(f"\033[8;{h};{w}t")
            sys.stdout.flush()
        except Exception:
            pass

    def _sync_screen_buffer_chars(self, cols: int, rows: int) -> None:
        """Ask the console driver for a buffer at least as large as the visible grid."""
        try:
            STD_OUTPUT_HANDLE = ctypes.c_ulong(0xFFFFFFF5)
            self._kernel32.GetStdHandle.restype = wintypes.HANDLE
            hout = self._kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            c = _COORD()
            c.X = ctypes.c_short(min(max(cols, 40), 9999))
            c.Y = ctypes.c_short(min(max(rows, 25), 9999))
            self._kernel32.SetConsoleScreenBufferSize.argtypes = [wintypes.HANDLE, _COORD]
            self._kernel32.SetConsoleScreenBufferSize.restype = wintypes.BOOL
            self._kernel32.SetConsoleScreenBufferSize(hout, c)
        except Exception:
            pass

    def _fill_monitor_work_area(self) -> None:
        """
        Resize the *top-level* host window to the current monitor work area, then
        nudge Windows Terminal via a VT resize sequence when applicable.
        """
        if not self._enabled:
            return
        MONITOR_DEFAULTTONEAREST = 2
        SWP_NOZORDER = 0x0004
        SWP_SHOWWINDOW = 0x0040

        target = self._host_hwnd_for_resize()
        hwnd_console = self._kernel32.GetConsoleWindow()
        ref = target or hwnd_console

        try:
            if not ref:
                wp = self._primary_work_area_pixels()
                if wp:
                    self._vt_resize_window_pixels(wp[0], wp[1])
                return

            hmon = self._user32.MonitorFromWindow(ref, MONITOR_DEFAULTTONEAREST)
            if not hmon:
                self._user32.ShowWindow(ref, self.SW_MAXIMIZE)
                return
            mi = _MONITORINFO()
            mi.cbSize = ctypes.sizeof(_MONITORINFO)
            if not self._user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                self._user32.ShowWindow(ref, self.SW_MAXIMIZE)
                return
            w = mi.rcWork
            cx = int(w.right - w.left)
            cy = int(w.bottom - w.top)

            # Top-level frame: some WT builds respond better to SC_MAXIMIZE via PostMessage than ShowWindow alone.
            WM_SYSCOMMAND = 0x0112
            SC_MAXIMIZE = 0xF030
            try:
                self._user32.BringWindowToTop(ref)
            except Exception:
                pass
            self._user32.ShowWindow(ref, self.SW_MAXIMIZE)
            _time.sleep(0.06)
            try:
                self._user32.PostMessageW(ref, WM_SYSCOMMAND, ctypes.c_uint(SC_MAXIMIZE), ctypes.c_long(0))
            except Exception:
                pass
            _time.sleep(0.12)
            self._user32.SetWindowPos(
                ref,
                0,
                int(w.left),
                int(w.top),
                max(cx, 200),
                max(cy, 120),
                SWP_NOZORDER | SWP_SHOWWINDOW,
            )

            # WT + pwsh: VT resize tracks the pane when Win32 targets the wrong HWND.
            self._vt_resize_window_pixels(cx, cy)
        except Exception:
            try:
                if ref:
                    self._user32.ShowWindow(ref, self.SW_MAXIMIZE)
            except Exception:
                pass

    def set_min_font_and_maximize(self, font_height: int = 8) -> tuple[int, int]:
        """Shrink console font, maximize window, return new (cols, rows). Best-effort."""
        if self._enabled and self._kernel32:
            try:
                STD_OUTPUT_HANDLE = ctypes.c_ulong(0xFFFFFFF5)  # -11 as DWORD
                hout = self._kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
                self._kernel32.GetStdHandle.restype = ctypes.c_void_p

                fi = _CONSOLE_FONT_INFOEX()
                fi.cbSize        = ctypes.sizeof(fi)
                fi.nFont         = 0
                fi.dwFontSize.X  = 0            # width: auto
                fi.dwFontSize.Y  = font_height  # height: e.g. 8 px
                fi.FontFamily    = 0x36         # FF_MODERN | FIXED_PITCH | TMPF_TRUETYPE
                fi.FontWeight    = 400
                fi.FaceName      = "Consolas"

                self._kernel32.SetCurrentConsoleFontEx.restype = wintypes.BOOL
                self._kernel32.SetCurrentConsoleFontEx(
                    hout, ctypes.c_bool(False), ctypes.byref(fi)
                )
            except Exception:
                pass  # non-fatal: continue without font resize

        if self._enabled:
            self._fill_monitor_work_area()
            _time.sleep(0.4)  # let the host reflow cells after pixel resize

        try:
            sz = os.get_terminal_size()
            self._sync_screen_buffer_chars(sz.columns, sz.lines)
            return sz.columns, sz.lines
        except OSError:
            return self._saved_cols, self._saved_rows

    def fit_for_ultra(self, target_cols: int = 1600, min_font: int = 4) -> tuple[int, int]:
        """
        Shrink the console font (down to *min_font* px height) and maximize so the
        column count approaches *target_cols* when the display allows.

        Important: ``acquire()`` sets a small ``mode con`` buffer; that caps visible
        columns even after maximize. We expand the screen buffer first so tiny fonts
        can actually increase the column count.
        """
        # Windows conhost: buffer size from initial ``mode con`` limits the grid.
        # Expand before shrinking font / maximizing (values clamped by the OS).
        want_cols = max(220, min(target_cols + 80, 650))
        want_rows = max(55, 100)
        self._mode_con(want_cols, want_rows)
        _time.sleep(0.1)

        best: tuple[int, int] = (self._saved_cols, self._saved_rows)
        for fh in range(8, min_font - 1, -1):
            cols, rows = self.set_min_font_and_maximize(font_height=fh)
            best = (cols, rows)
            if cols >= target_cols:
                break

        # Second fill: font + buffer are set; one more work-area snap helps WT/conhost.
        self._fill_monitor_work_area()
        _time.sleep(0.25)

        # Sync screen buffer to measured grid (and pick up any extra columns).
        try:
            sz = os.get_terminal_size()
            self._mode_con(max(sz.columns, 40), max(sz.lines, 25))
            best = (sz.columns, sz.lines)
        except OSError:
            pass

        return best

    def release(self) -> None:
        """Restore prior resize behavior and the original console dimensions."""
        if not self._locked:
            return

        self._set_resize_enabled(True)
        self._mode_con(self._saved_cols, self._saved_rows)
        self._locked = False
