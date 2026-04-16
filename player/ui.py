"""Terminal UI: startup menu and in-player HUD."""

import os
import re
import sys

from .ascii import CHARSETS, DETAIL_LEVELS, resolve_detail_label
from .modes import MODE_PRESETS

# ── ANSI helpers ──────────────────────────────────────────────────────────────
RST    = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[36m"
BCYAN  = "\033[1;96m"
YELLOW = "\033[33m"
BYLLW  = "\033[1;33m"
GREEN  = "\033[92m"
WHITE  = "\033[97m"
GRAY   = "\033[90m"
MGNT   = "\033[95m"
BLUE   = "\033[94m"
RED    = "\033[91m"

THEMES = [
    {
        "name": "Ocean",
        "frame": BCYAN,
        "accent": CYAN,
        "highlight": BYLLW,
        "text": WHITE,
        "muted": GRAY,
        "success": GREEN,
        "warning": BYLLW,
        "shades": [GRAY, CYAN, BCYAN, WHITE],
    },
    {
        "name": "Sunset",
        "frame": YELLOW,
        "accent": RED,
        "highlight": MGNT,
        "text": WHITE,
        "muted": GRAY,
        "success": YELLOW,
        "warning": RED,
        "shades": [GRAY, RED, YELLOW, WHITE],
    },
    {
        "name": "Matrix",
        "frame": GREEN,
        "accent": GREEN,
        "highlight": WHITE,
        "text": GREEN,
        "muted": GRAY,
        "success": GREEN,
        "warning": WHITE,
        "shades": [GRAY, GREEN, GREEN + BOLD, WHITE],
    },
    {
        "name": "Studio",
        "frame": MGNT,
        "accent": BLUE,
        "highlight": BYLLW,
        "text": WHITE,
        "muted": GRAY,
        "success": BLUE,
        "warning": MGNT,
        "shades": [GRAY, BLUE, MGNT, WHITE],
    },
]

VIDEO_EXTS = {".mp4", ".webm", ".avi", ".mkv", ".mov", ".flv", ".m4v"}

# Strip ANSI SGR sequences for measuring visible width (avoid HUD line wrap).
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _w(s: str) -> None:
    sys.stdout.write(s)
    sys.stdout.flush()


def _term() -> os.terminal_size:
    try:
        return os.get_terminal_size()
    except OSError:
        class _Sz:
            columns = 120
            lines   = 40
        return _Sz()  # type: ignore[return-value]


def _theme(theme_idx: int) -> dict[str, str]:
    return THEMES[theme_idx % len(THEMES)]


def theme_color_ramp(theme_idx: int) -> list[str]:
    theme = _theme(theme_idx)
    shades = list(theme["shades"])
    return [shades[0], shades[1], shades[1], shades[2], shades[3]]


def _mode_strip(active: str, theme: dict[str, str]) -> str:
    """Render the  1 Chill · 2 High · 3 Ultra  selector strip."""
    parts = []
    for key, mkey in (("1", "chill"), ("2", "high"), ("3", "ultra")):
        label = str(MODE_PRESETS[mkey]["label"])
        if active == mkey:
            parts.append(f"{theme['highlight']}[{key}] {BOLD}{label}{RST}")
        else:
            parts.append(f"{theme['muted']}[{key}] {label}{RST}")
    return (f"{theme['muted']} · {RST}").join(parts)


# ══════════════════════════════════════════════════════════════════════════════
#  LOADING SCREEN
# ══════════════════════════════════════════════════════════════════════════════

def draw_loading(title: str, theme_idx: int = 0) -> None:
    """Shown while audio is being extracted (instant if already cached)."""
    theme = _theme(theme_idx)
    t   = _term()
    W   = min(t.columns - 4, 62)
    pad = " " * max(0, (t.columns - W - 2) // 2)
    _w(
        "\033[H\033[J\n"
        f"{pad}{theme['frame']}╔{'═' * W}╗{RST}\n"
        f"{pad}{theme['frame']}║{'  ASCII TERMINAL VIDEO PLAYER  '.center(W)}║{RST}\n"
        f"{pad}{theme['frame']}╚{'═' * W}╝{RST}\n\n"
        f"{pad}  {theme['muted']}Loading  {RST}{BOLD}{title}{RST}\n"
        f"{pad}  {theme['accent']}Preparing audio track...{RST}\n"
        f"{pad}  {theme['muted']}(cached after first play){RST}\n"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  STARTUP MENU
# ══════════════════════════════════════════════════════════════════════════════

VIDEOS_DIR = "videos"
AUDIO_DIR  = "audio_extracted"
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"}


def scan_videos() -> list[str]:
    """Return sorted list of video filenames inside videos/."""
    if not os.path.isdir(VIDEOS_DIR):
        os.makedirs(VIDEOS_DIR, exist_ok=True)
    return sorted(
        f for f in os.listdir(VIDEOS_DIR)
        if os.path.splitext(f)[1].lower() in VIDEO_EXTS
    )


def video_full_path(filename: str) -> str:
    """Resolve a filename from the videos/ dir to an absolute path."""
    return os.path.join(VIDEOS_DIR, filename)


def next_video_in_library(video_path: str) -> str | None:
    """
    If *video_path* is a file directly under videos/ (same order as scan_videos),
    return the absolute path of the next file in sorted order; otherwise None.
    """
    try:
        abs_cur = os.path.normpath(os.path.abspath(video_path))
        abs_dir = os.path.normpath(os.path.abspath(VIDEOS_DIR))
    except OSError:
        return None
    if os.path.dirname(abs_cur) != abs_dir:
        return None
    files = scan_videos()
    base = os.path.basename(abs_cur)
    idx = None
    for i, name in enumerate(files):
        if name.lower() == base.lower():
            idx = i
            break
    if idx is None or idx + 1 >= len(files):
        return None
    return os.path.normpath(video_full_path(files[idx + 1]))


def scan_audio() -> list[str]:
    """Return sorted list of audio filenames inside audio_extracted/."""
    if not os.path.isdir(AUDIO_DIR):
        os.makedirs(AUDIO_DIR, exist_ok=True)
    return sorted(
        f for f in os.listdir(AUDIO_DIR)
        if os.path.splitext(f)[1].lower() in AUDIO_EXTS
    )


def audio_full_path(filename: str) -> str:
    return os.path.join(AUDIO_DIR, filename)


def draw_menu(
    videos: list[str],
    sel: int,
    theme_idx: int = 0,
    tab: int = 0,
    audio_files: list[str] | None = None,
) -> None:
    theme       = _theme(theme_idx)
    t           = _term()
    W           = min(t.columns - 4, 62)
    pad         = " " * max(0, (t.columns - W - 2) // 2)
    audio_files = audio_files or []
    lines       = ["\033[H\033[J"]

    # ── logo box ──────────────────────────────────────────────────────────────
    logo     = f"  ASCII TERMINAL VIDEO PLAYER  [{theme['name']}]  "
    subtitle = "A terminal cinema for local videos"
    lines += [
        "\n",
        f"{pad}{theme['frame']}╔{'═' * W}╗{RST}\n",
        f"{pad}{theme['frame']}║{logo.center(W)}║{RST}\n",
        f"{pad}{theme['frame']}║{subtitle.center(W)}║{RST}\n",
        f"{pad}{theme['frame']}╚{'═' * W}╝{RST}\n",
        "\n",
    ]

    # ── tab bar ───────────────────────────────────────────────────────────────
    tab_videos = (
        f"{theme['highlight']}{BOLD}[ VIDEOS ]{RST}" if tab == 0
        else f"{theme['muted']}  VIDEOS  {RST}"
    )
    tab_audio = (
        f"{theme['highlight']}{BOLD}[ AUDIO ]{RST}" if tab == 1
        else f"{theme['muted']}  AUDIO  {RST}"
    )
    lines.append(
        f"{pad}  {tab_videos}  {tab_audio}  "
        f"{theme['muted']}(TAB to switch){RST}\n\n"
    )

    # ── file list ─────────────────────────────────────────────────────────────
    if tab == 0:
        items    = videos
        src_dir  = VIDEOS_DIR
        empty_msg = "No video files found in this folder."
        # Show mode strip only on video tab
        lines.append(
            f"{pad}  {theme['muted']}Modes:{RST}  {_mode_strip('custom', theme)}\n\n"
        )
    else:
        items    = audio_files
        src_dir  = AUDIO_DIR
        empty_msg = "No audio files found. Use  python main.py -a <url>  to download."

    if items:
        lines.append(f"{pad}  {theme['muted']}Files in  {BOLD}{src_dir}/{RST}{theme['muted']}:{RST}\n\n")
        for i, v in enumerate(items):
            label = v if len(v) <= W - 6 else v[: W - 9] + "…"
            if i == sel:
                bar = f"{theme['highlight']}▶  {label:<{W - 6}}{RST}"
                lines.append(f"{pad}  {theme['highlight']}┃{RST} {bar}\n")
            else:
                lines.append(f"{pad}    {theme['muted']}·{RST} {theme['text']}{label}{RST}\n")
    else:
        lines.append(f"{pad}  {theme['muted']}{empty_msg}{RST}\n")

    # ── footer ────────────────────────────────────────────────────────────────
    lines += [
        f"\n{pad}  {theme['muted']}{'-' * (W - 2)}{RST}\n",
        f"{pad}  {theme['muted']}UP/DOWN{RST} Navigate  "
        f"{theme['muted']}ENTER{RST} Play  "
        f"{theme['muted']}TAB{RST} Switch tab  "
        f"{theme['muted']}T{RST} Theme  "
        f"{theme['muted']}P{RST} Path  "
        f"{theme['muted']}Q{RST} Quit\n",
        f"{pad}  {theme['muted']}Tip:{RST} Use {theme['highlight']}--add <url>{RST} for video  "
        f"or {theme['highlight']}-a <url>{RST} for audio.\n",
    ]

    _w("".join(lines))


# ══════════════════════════════════════════════════════════════════════════════
#  IN-PLAYER HUD
# ══════════════════════════════════════════════════════════════════════════════

def draw_hud(
    ascii_frame : str,
    frame_num   : int,
    total       : int,
    fps         : float,
    asc_h       : int,
    title       : str,
    mode_name   : str,
    charset_idx : int,
    detail_idx  : int,
    auto_detail : bool,
    colorized   : bool,
    theme_idx   : int,
    paused      : bool,
    term_cols   : int | None = None,  # ignored; layout uses live os.get_terminal_size()
) -> None:
    """
    Draw chrome + video using one cursor move per row. Sequential newlines break
    layout when any line wraps; explicit \\033[row;1H avoids that.
    *asc_h* is container_rows (letterboxed block height in lines).
    """
    theme = _theme(theme_idx)
    # Always use the real buffer width; a cached column count can exceed the window and wrap.
    cols = max(_term().columns, 20)

    # timecodes
    elapsed = frame_num / max(fps, 1)
    tot_sec = total     / max(fps, 1)
    em, es  = divmod(int(elapsed), 60)
    tm, ts  = divmod(int(tot_sec), 60)
    tc      = f"{em:02d}:{es:02d} / {tm:02d}:{ts:02d}"

    if paused:
        state_str = f"{theme['warning']}PAUSED{RST}"
    else:
        state_str = f"{theme['success']}PLAYING{RST}"

    cs_name  = CHARSETS[charset_idx][1]
    cs_label = f"{theme['accent']}{cs_name}{RST}{theme['muted']}({charset_idx + 1}/{len(CHARSETS)}){RST}"
    detail_name = resolve_detail_label(detail_idx, auto_detail)
    detail_label = f"{theme['highlight']}{detail_name}{RST}{theme['muted']}({detail_idx + 1}/{len(DETAIL_LEVELS)}){RST}"
    theme_label = f"{theme['frame']}{THEMES[theme_idx % len(THEMES)]['name']}{RST}"
    color_label = f"{theme['accent']}COLOR{RST}" if colorized else f"{theme['muted']}B/W{RST}"
    mode_label = f"{theme['accent']}ASCII CINEMA{RST}"

    fixed    = 2 + 10 + 2 + 2 + len(tc) + 2
    bar_w    = max(8, cols - fixed - 2)
    filled   = int((frame_num / max(total, 1)) * bar_w)
    bar      = f"{theme['accent']}{'=' * filled}{theme['muted']}{'-' * (bar_w - filled)}{RST}"

    t_label = title
    line2 = (
        f"{BOLD}{t_label}{RST}  {theme['muted']}|{RST}  {mode_label}  "
        f"{theme['muted']}|{RST}  {cs_label}  "
        f"{theme['muted']}|{RST}  {detail_label}  "
        f"{theme['muted']}|{RST}  {color_label}  "
        f"{theme['muted']}|{RST}  {theme_label}  "
        f"{theme['muted']}|{RST}  {theme['muted']}{fps:.0f} fps{RST}"
    )
    while len(_strip_ansi(line2)) > cols and len(t_label) > 12:
        t_label = t_label[:-2] + "…"
        line2 = (
            f"{BOLD}{t_label}{RST}  {theme['muted']}|{RST}  {mode_label}  "
            f"{theme['muted']}|{RST}  {cs_label}  "
            f"{theme['muted']}|{RST}  {detail_label}  "
            f"{theme['muted']}|{RST}  {color_label}  "
            f"{theme['muted']}|{RST}  {theme_label}  "
            f"{theme['muted']}|{RST}  {theme['muted']}{fps:.0f} fps{RST}"
        )

    hints = (
        f"{theme['muted']}SPACE/P{RST} pause  "
        f"{theme['muted']}←/→{RST} seek  "
        f"MODE {_mode_strip(mode_name, theme)}  "
        f"{theme['muted']}V{RST} charset  "
        f"{theme['muted']}M{RST} detail  "
        f"{theme['muted']}A{RST} auto  "
        f"{theme['muted']}C{RST} color  "
        f"{theme['muted']}T{RST} theme  "
        f"{theme['muted']}F{RST} fs  "
        f"{theme['muted']}H{RST} hud  "
        f"{theme['muted']}Q/ESC{RST} quit"
    )
    if len(_strip_ansi(hints)) > cols:
        hints_one = f"{theme['muted']}SPACE/P pause  ←/→ seek  MODE 1·2·3  Q quit{RST}"
    else:
        hints_one = hints

    ascii_lines = ascii_frame.split("\n")
    # Rows 1–2: chrome. Rows 3..2+len: video block. Progress/hints follow immediately after.
    progress_row = 3 + len(ascii_lines)

    parts: list[str] = [
        f"\033[1;1H\033[2K{theme['muted']}{'=' * cols}{RST}",
        f"\033[2;1H\033[2K{line2}",
    ]
    for i, aline in enumerate(ascii_lines):
        parts.append(f"\033[{3 + i};1H\033[2K{aline}")
    parts.append(f"\033[{progress_row};1H\033[2K{state_str}  [{bar}]  {BOLD}{tc}{RST}")
    parts.append(f"\033[{progress_row + 1};1H\033[2K{hints_one}")

    sys.stdout.write("".join(parts))
    sys.stdout.flush()


def draw_video_only(ascii_frame: str) -> None:
    """Draw only video content for a full-screen-like terminal experience."""
    sys.stdout.write("\033[H" + ascii_frame)
    sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO PLAYER
# ══════════════════════════════════════════════════════════════════════════════

_BAR_CHARS = " ▁▂▃▄▅▆▇█"


def make_audio_art(cols: int, rows: int, heights: list[float], theme_idx: int) -> str:
    """Render a spectrum-analyser bar chart. heights[i] is 0..1 per column."""
    theme = _theme(theme_idx)
    n     = len(heights)
    lines = []
    for r in range(rows):
        full_thresh = (rows - r) / rows
        part_thresh = full_thresh - 1 / rows
        line        = ""
        prev_color  = ""
        for col in range(cols):
            h = heights[col * n // cols] if n else 0.0
            if h >= full_thresh:
                color = theme["accent"]
                ch    = "█"
            elif h >= part_thresh:
                frac  = (h - part_thresh) * rows
                idx   = max(1, min(8, int(frac * 8) + 1))
                ch    = _BAR_CHARS[idx]
                color = theme["frame"]
            else:
                color = ""
                ch    = " "
            if color != prev_color:
                if prev_color:
                    line += RST
                if color:
                    line += color
                prev_color = color
            line += ch
        if prev_color:
            line += RST
        lines.append(line)
    return "\n".join(lines)


def draw_audio_hud(
    art      : str,
    elapsed  : float,
    total    : float,
    title    : str,
    paused   : bool,
    theme_idx: int,
    art_rows : int,
) -> None:
    theme = _theme(theme_idx)
    cols  = _term().columns

    em, es = divmod(int(elapsed), 60)
    tm, ts = divmod(int(max(total, elapsed)), 60)
    tc     = f"{em:02d}:{es:02d} / {tm:02d}:{ts:02d}"

    state_str   = f"{theme['warning']}PAUSED{RST}" if paused else f"{theme['success']}PLAYING{RST}"
    theme_label = f"{theme['frame']}{THEMES[theme_idx % len(THEMES)]['name']}{RST}"

    fixed  = 2 + 10 + 2 + 2 + len(tc) + 2
    bar_w  = max(8, cols - fixed - 2)
    ratio  = (elapsed / total) if total > 0 else 0.0
    filled = int(ratio * bar_w)
    bar    = f"{theme['accent']}{'=' * filled}{theme['muted']}{'-' * (bar_w - filled)}{RST}"

    max_t   = cols - 24
    t_label = title if len(title) <= max_t else title[: max_t - 1] + "…"

    hints = (
        f"{theme['muted']}SPACE/P{RST} pause  "
        f"{theme['muted']}T{RST} theme  "
        f"{theme['muted']}Q/ESC{RST} quit"
    )

    buf = [
        f"\033[H\033[2K {theme['muted']}{'═' * max(cols - 2, 10)}{RST}\n",
        f"\033[2K {BOLD}{t_label}{RST}  "
        f"{theme['muted']}|{RST}  {theme['accent']}♫ AUDIO{RST}  "
        f"{theme['muted']}|{RST}  {theme_label}\n",
        "\033[2K\n",                              # blank spacer row
        art,                                      # rows 4 … 3+art_rows
        f"\033[{art_rows + 4};1H\033[2K  {state_str}  [{bar}]  {BOLD}{tc}{RST}",
        f"\033[{art_rows + 5};1H\033[2K  {hints}",
    ]

    sys.stdout.write("".join(buf))
    sys.stdout.flush()
