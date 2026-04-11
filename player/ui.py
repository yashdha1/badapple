"""Terminal UI: startup menu and in-player HUD."""

import os
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


def draw_menu(videos: list[str], sel: int, theme_idx: int = 0) -> None:
    theme = _theme(theme_idx)
    t     = _term()
    W     = min(t.columns - 4, 62)          # inner box width
    pad   = " " * max(0, (t.columns - W - 2) // 2)
    lines = ["\033[H\033[J"]

    # ── logo box ──────────────────────────────────────────────────────────────
    logo = f"  ASCII TERMINAL VIDEO PLAYER  [{theme['name']}]  "
    subtitle = "A terminal cinema for local videos"
    lines += [
        "\n",
        f"{pad}{theme['frame']}╔{'═' * W}╗{RST}\n",
        f"{pad}{theme['frame']}║{logo.center(W)}║{RST}\n",
        f"{pad}{theme['frame']}║{subtitle.center(W)}║{RST}\n",
        f"{pad}{theme['frame']}╚{'═' * W}╝{RST}\n",
        "\n",
    ]

    # ── status strip ─────────────────────────────────────────────────────────
    stats = f"Library: {len(videos)} videos"
    actions = "T Theme  |  P Path  |  ENTER Play"
    lines += [
        f"{pad}  {theme['muted']}{stats}{RST}  {theme['muted']}|{RST}  {theme['accent']}{actions}{RST}\n"
    ]

    # ── mode strip ───────────────────────────────────────────────────────────
    lines += [
        f"{pad}  {theme['muted']}Modes:{RST}  {_mode_strip('custom', theme)}\n\n"
    ]

    # ── file list ─────────────────────────────────────────────────────────────
    if videos:
        lines.append(f"{pad}  {theme['muted']}Videos in  {BOLD}{VIDEOS_DIR}/{RST}{theme['muted']}:{RST}\n\n")
        for i, v in enumerate(videos):
            label = v if len(v) <= W - 6 else v[: W - 9] + "…"
            if i == sel:
                bar = f"{theme['highlight']}▶  {label:<{W - 6}}{RST}"
                lines.append(f"{pad}  {theme['highlight']}┃{RST} {bar}\n")
            else:
                lines.append(f"{pad}    {theme['muted']}·{RST} {theme['text']}{label}{RST}\n")
    else:
        lines.append(f"{pad}  {theme['muted']}No video files found in this folder.{RST}\n")

    # ── footer ────────────────────────────────────────────────────────────────
    lines += [
        f"\n{pad}  {theme['muted']}{'-' * (W - 2)}{RST}\n",
        f"{pad}  {theme['muted']}UP/DOWN{RST} Navigate  "
        f"{theme['muted']}ENTER{RST} Play  "
        f"{theme['muted']}P{RST} Custom path  "
        f"{theme['muted']}T{RST} Theme  "
        f"{theme['muted']}Q{RST} Quit\n",
        f"{pad}  {theme['muted']}Tip:{RST} Use {theme['highlight']}--add <url>{RST} from CLI to download quickly.\n",
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
) -> None:
    theme = _theme(theme_idx)
    cols = _term().columns

    # timecodes
    elapsed = frame_num / max(fps, 1)
    tot_sec = total     / max(fps, 1)
    em, es  = divmod(int(elapsed), 60)
    tm, ts  = divmod(int(tot_sec), 60)
    tc      = f"{em:02d}:{es:02d} / {tm:02d}:{ts:02d}"

    # play/pause icon
    if paused:
        state_str = f"{theme['warning']}PAUSED{RST}"
    else:
        state_str = f"{theme['success']}PLAYING{RST}"

    # charset label
    cs_name  = CHARSETS[charset_idx][1]
    cs_label = f"{theme['accent']}{cs_name}{RST}{theme['muted']}({charset_idx + 1}/{len(CHARSETS)}){RST}"
    detail_name = resolve_detail_label(detail_idx, auto_detail)
    detail_label = f"{theme['highlight']}{detail_name}{RST}{theme['muted']}({detail_idx + 1}/{len(DETAIL_LEVELS)}){RST}"
    theme_label = f"{theme['frame']}{THEMES[theme_idx % len(THEMES)]['name']}{RST}"
    color_label = f"{theme['accent']}COLOR{RST}" if colorized else f"{theme['muted']}B/W{RST}"
    mode_label = f"{theme['accent']}ASCII CINEMA{RST}"

    # dynamic progress bar fills remaining terminal width
    fixed    = 2 + 10 + 2 + 2 + len(tc) + 2   # state(10) + brackets + time
    bar_w    = max(8, cols - fixed - 2)
    filled   = int((frame_num / max(total, 1)) * bar_w)
    bar      = f"{theme['accent']}{'=' * filled}{theme['muted']}{'-' * (bar_w - filled)}{RST}"

    # title truncated to fit
    max_t   = cols - len(cs_name) - 20
    t_label = title if len(title) <= max_t else title[: max_t - 1] + "…"

    hints = (
        f"{theme['muted']}SPACE/P{RST} pause  "
        f"{theme['muted']}V{RST} charset  "
        f"{theme['muted']}M{RST} detail  "
        f"{theme['muted']}A{RST} auto  "
        f"{theme['muted']}C{RST} color  "
        f"{theme['muted']}T{RST} theme  "
        f"{theme['muted']}F{RST} fullscreen  "
        f"{theme['muted']}H{RST} hud  "
        f"{theme['muted']}Q/ESC{RST} quit"
    )

    buf = [
        f"\033[H\033[2K {theme['muted']}{'=' * max(cols - 2, 10)}{RST}\n",
        # row 2: title bar
        "\033[2K",
        f" {BOLD}{t_label}{RST}  {theme['muted']}|{RST}  {mode_label}  "
        f"{theme['muted']}|{RST}  {cs_label}  "
        f"{theme['muted']}|{RST}  {detail_label}  "
        f"{theme['muted']}|{RST}  {color_label}  "
        f"{theme['muted']}|{RST}  {theme_label}  "
        f"{theme['muted']}|{RST}  {theme['muted']}{fps:.0f} fps{RST}\n",
        # row 3: dedicated mode strip
        f"\033[2K  {_mode_strip(mode_name, theme)}\n",
        # rows 4 … asc_h+3: ascii frame
        ascii_frame,
        # row asc_h+4: progress bar
        f"\033[{asc_h + 4};1H\033[2K  {state_str}  [{bar}]  {BOLD}{tc}{RST}",
        # row asc_h+5: hints
        f"\033[{asc_h + 5};1H\033[2K  {hints}",
    ]

    sys.stdout.write("".join(buf))
    sys.stdout.flush()


def draw_video_only(ascii_frame: str) -> None:
    """Draw only video content for a full-screen-like terminal experience."""
    sys.stdout.write("\033[H" + ascii_frame)
    sys.stdout.flush()
