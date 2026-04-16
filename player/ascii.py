"""ASCII charset definitions, frame-to-ASCII conversion, and canvas math."""

import os
import cv2
import numpy as np

# Prefer Lanczos for upscales when available (OpenCV 4+).
_UP = getattr(cv2, "INTER_LANCZOS4", cv2.INTER_CUBIC)

# Pre-built ANSI-256 foreground escape sequences — avoids f-string formatting in the RLE hot loop.
_ANSI_FG: list[str] = [f"\033[38;5;{i}m" for i in range(256)]

# True-colour (24-bit) support: Windows Terminal sets COLORTERM=truecolor; also detect WT_SESSION.
_TRUECOLOR: bool = (
    os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")
    or bool(os.environ.get("WT_SESSION") or os.environ.get("WT_PROFILE_ID"))
)

# Upper bound for ultra horizontal resolution (terminal cols cap the real size).
ULTRA_MAX_WIDTH: int = 1600

CHARSETS: list[tuple[str, str]] = [ 
    (" .'`^\",;Il!i><~+_-?][}{1)(|/MW&8%B$",    "Detailed"),
    (".,:;i\|/BC0@",             "Simple"),
    (" ⁘⁙⁚⁛⁜",                   "Dot Matrix Dense"),
    (" /|\\|/|\\|",                  "Flow Grid"),     
    (" .,:;i1tfLCGθ",                                                          "Simple"),
    (" -+*#?",                                                                   "Minimal"),
    ("@%#*+=-:. ",                                                               "Inverse"),
    (" ░▒▓█",                                                                    "Block"),
    (" .oO0θ#",                                                                   "Soft Dot"),
    (" `.-:=+*#%@",                                                              "Gradient"),
    (" .,:irsXA253hMHGS#9B&",                                                   "Retro"),
    (" _/|\\-",                                                            "Wire"),
    # --- Density / Shading ---
    (" ·:;+=xX$&@",                                         "Punchy"),        # High contrast, snappy
    (" ░▒▓▓█▓▒░ ",                                          "Pulse"),         # Symmetric for breathing effects
    (" .·°oO◉●",                                            "Bubble"),        # Smooth circular feel
    (" ⠀⠁⠃⠇⠏⠟⠿⡿⣿",                                        "Braille"),       # Braille dots — very smooth gradient
    (" ▁▂▃▄▅▆▇█",                                           "Bar"),          # Block bars — great for waveforms
    (" ▏▎▍▌▋▊▉█",                                           "Slim Bar"),     # Horizontal fill — fluid motion

    # --- Geometric / Structured ---
    (" ╌╍═╔╦╗",                                             "Box Draw"),     # Box-drawing — circuit/grid animations
    (" ▖▗▘▙▚▛▜▝▞▟█",                                        "Quadrant"),     # Sub-character quads, silky gradients
    (" ◜◝◞◟◠◡○◎●",                                          "Orbit"),        # Good for circular/spinning animations
    (" ⬡⬢",                                                 "Hex"),          # Hexagonal tiling

    # --- Symbol / Thematic ---
    (" ·✦✧⋆★✶✷✸✹",                                         "Starfield"),    # Space/particle animations
    (" ∙∘○◯●",                                              "Void"),         # Minimalist depth
    (" ⣀⣄⣤⣦⣶⣷⣿",                                          "Braille Heavy"), # Denser braille — smoother than Block
    (" ~≈≋∿⌇",                                              "Wave"),         # Fluid/water motion
    (r" .:!|)(\/[]{}",                                       "Glitch"),       # Chaotic glitch aesthetic

    # --- High-fidelity for animation ---
    (" .·˙∘°οΟ0█",                                          "Neon Glow"),    # Smooth light bloom effect
    (" ⡀⡄⡆⡇⣇⣧⣷⣿",                                         "Braille Sweep"), # Left-to-right sweep, very cinematic
    (" ▴▵△▲",                                               "Triangle"),     # For crystalline/geometric scenes
    (" ,;:<>[]|Il!1i",                                       "Thin Noise"),   # Dense, fine-grained noise/static

    # --- Corner & Edge Emphasis ---
    (" ┘┐┌└┼─│╴╵╶╷",                           "Corner Sharp"),   # Hard 90° corners, grid feel
    (" ╰╯╮╭│─",                                 "Corner Round"),   # Rounded corners, softer flow
    (" ┛┓┏┗╋━┃",                                "Corner Bold"),    # Thick corners, strong structure
    (" ╝╗╔╚╬═║",                                "Corner Double"),  # Double-line corners, ornate
    (" ▗▖▝▘",                                   "Corner Quad"),    # Quarter-block corners only

    # --- Directional / Flow ---
    (" ←↑→↓↖↗↘↙",                              "Arrow Flow"),     # Directional energy map
    (" ⇐⇑⇒⇓⇔⇕",                               "Arrow Bold"),     # Bold arrows, strong motion
    (" ▹▸◂◃△▽",                                 "Chevron"),        # Arrowhead shapes, fast feel
    (" ╱╲╳",                                    "Diagonal"),       # Diagonal cuts, slash effects
    (" ⟋⟍⟆⟇",                                  "Slash"),          # Stylized diagonals

    # --- Frame / Structure Highlight ---
    (" ▕▏▔▁",                                   "Edge Thin"),      # Thin single-side edges
    (" ▐▌▀▄",                                   "Edge Half"),      # Half-block edges — sharp borders
    (" ┄┆┈┊",                                   "Dashed"),         # Dashed structure, scanning effect
    (" ╒╓╕╖╙╜╛╞╟╡╢╤╥╧╨╪╫",                     "Mixed Box"),      # Mixed single/double box draw
    (" ▉▊▋▌▍▎▏",                               "Left Fade"),      # Fade from left wall outward

    # --- Particle / Spark ---
    (" ·✦✺❋❊❉❈",                               "Spark"),          # Expanding spark burst
    (" ˖ ˙ ⁺ ∘ ⊹ ✦ ✧",                        "Glimmer"),        # Subtle light glimmer
    (" ⁘⁙⁚⁛",                                  "Dot Matrix"),     # Arranged dot patterns
    (" ⋰⋱⋮⋯",                                  "Ellipsis"),       # Trailing motion dots
    (" ∴∵∶∷",                                   "Reason"),         # Dense logical dot clusters

    # --- Organic / Fluid ---
    (" ꩜ ꩝ 〇 ◌ ◍ ◎ ● ◉",                     "Ripple"),         # Expanding rings, sonar/water
    (" ╭─╮│ │╰─╯",                             "Bubble Box"),     # Rounded box outline pieces
    (" ⌁⌂⌃⌄⌅⌆",                               "Tech"),           # Technical symbol feel
    (" ≀⋮⋯⋰⋱",                                 "Scatter"),        # Scattered asymmetric dots 
]

DETAIL_LEVELS: list[dict[str, float | str]] = [
    {"name": "Native", "scale": 1.0, "clahe": 0.0, "sharpen": 0.0, "edges": 0.0},
    {"name": "Sharp", "scale": 1.35, "clahe": 2.2, "sharpen": 0.50, "edges": 0.12},
    {"name": "Ultra", "scale": 1.70, "clahe": 3.0, "sharpen": 0.85, "edges": 0.18},
    {"name": "Hyper", "scale": 2.10, "clahe": 4.2, "sharpen": 1.20, "edges": 0.26},
]

AUTO_DETAIL_NAME = "Auto"

# Terminal monospace chars are roughly twice as tall as they are wide.
# char_pixel_width / char_pixel_height ≈ 0.5
CHAR_ASPECT: float = 0.5

# Default HUD rows taken by title bar + progress bar + hints + 1 margin
_DEFAULT_HUD_ROWS = 4


# ── ANSI 256-colour helpers ───────────────────────────────────────────────────

def _c6(v: np.ndarray) -> np.ndarray:
    """Vectorised: map each 0-255 value to a 0-5 ANSI-256 colour-cube index."""
    return np.clip(np.where(v < 48, 0, np.where(v < 115, 1, (v.astype(np.int32) - 35) // 40)), 0, 5).astype(np.uint8)


def _compute_color_codes(color_frame: np.ndarray) -> np.ndarray:
    """Return a (H, W) uint8 array of ANSI-256 colour indices for BGR color_frame."""
    r = color_frame[:, :, 2]
    g = color_frame[:, :, 1]
    b = color_frame[:, :, 0]
    return (16 + 36 * _c6(r) + 6 * _c6(g) + _c6(b)).astype(np.uint8)


def _gamma_u8(gray: np.ndarray, gamma: float = 2.2) -> np.ndarray:
    """Perceptual gamma for luminance before mapping to charset indices."""
    x = gray.astype(np.float32) / 255.0
    return np.clip(np.power(np.maximum(x, 1e-6), 1.0 / gamma) * 255.0, 0, 255).astype(np.uint8)


def compute_canvas(
    vid_w: int,
    vid_h: int,
    term_cols: int,
    term_rows: int,
    hud_rows: int = _DEFAULT_HUD_ROWS,
    keep_cinematic_16_9: bool = True,
    max_width: int | None = None,
) -> tuple[int, int, int, int, int]:
    """
    Compute ASCII canvas dimensions that:
      • preserve the video's original aspect ratio
            • place it inside a 16:9 container (letterbox / pillarbox as needed)
                when keep_cinematic_16_9=True
            • or use the full terminal rectangle when keep_cinematic_16_9=False

    Returns: (asc_w, asc_h, pad_top, pad_left, container_rows)
    """
    avail_cols = term_cols
    avail_rows = max(term_rows - hud_rows, 10)

    if keep_cinematic_16_9:
        # ── 16:9 container in terminal cells ─────────────────────────────────
        # Apparent width  = container_cols * CHAR_ASPECT
        # Apparent height = container_rows * 1
        # → container_rows = container_cols * CHAR_ASPECT * 9/16
        container_cols = avail_cols
        container_rows = int(container_cols * CHAR_ASPECT * 9 / 16)
        if container_rows > avail_rows:
            container_rows = avail_rows
            container_cols = int(container_rows * 16 / (9 * CHAR_ASPECT))
    else:
        # Use all available rows/cols for true video-only mode.
        container_cols = avail_cols
        container_rows = avail_rows

    # ── fit video inside container, maintaining its AR ───────────────────────
    # asc_w * CHAR_ASPECT / asc_h = vid_w / vid_h
    vid_ar = vid_w / max(vid_h, 1)
    asc_w  = min(container_cols, avail_cols)
    asc_h  = int(asc_w * CHAR_ASPECT / vid_ar)

    if asc_h > container_rows:
        asc_h = container_rows
        asc_w = int(asc_h * vid_ar / CHAR_ASPECT)

    # ── ultra-mode pixel cap (480p-class horizontal detail) ───────────────────
    if max_width is not None and asc_w > max_width:
        asc_w = max_width
        asc_h = int(asc_w * CHAR_ASPECT / vid_ar)
        if asc_h > container_rows:
            asc_h = container_rows
            asc_w = int(asc_h * vid_ar / CHAR_ASPECT)

    # Vertical: center inside the 16:9 container; horizontal: center in full terminal
    # width so the image stays centered when container_cols < avail_cols (short windows).
    pad_top = (container_rows - asc_h) // 2
    pad_left = max(0, (avail_cols - asc_w) // 2)

    return asc_w, asc_h, pad_top, pad_left, container_rows


def apply_letterbox(
    ascii_frame: str, pad_top: int, pad_left: int, asc_w: int, container_rows: int
) -> str:
    """Wrap *ascii_frame* in blank lines/spaces to fill the 16:9 container."""
    spc    = " " * pad_left
    blank  = spc + " " * asc_w
    lines  = ascii_frame.split("\n")
    padded = [spc + line for line in lines]
    bot    = max(0, container_rows - len(lines) - pad_top)
    return "\n".join([blank] * pad_top + padded + [blank] * bot)


def _frame_complexity(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 80, 160)
    edge_density = float(edges.mean()) / 255.0
    contrast = min(float(gray.std()) / 64.0, 1.0)
    gradient = cv2.Sobel(gray, cv2.CV_32F, 1, 1, ksize=3)
    texture = min(float(np.mean(np.abs(gradient))) / 48.0, 1.0)
    return min(1.0, 0.45 * edge_density + 0.35 * contrast + 0.20 * texture)


def resolve_detail_label(detail_idx: int, auto_detail: bool) -> str:
    if auto_detail:
        return AUTO_DETAIL_NAME
    return str(DETAIL_LEVELS[detail_idx % len(DETAIL_LEVELS)]["name"])


def _detail_profile(gray: np.ndarray, detail_idx: int, auto_detail: bool) -> dict[str, float | str]:
    profile = dict(DETAIL_LEVELS[detail_idx % len(DETAIL_LEVELS)])
    if not auto_detail:
        return profile

    complexity = _frame_complexity(gray)
    profile["name"] = AUTO_DETAIL_NAME
    profile["scale"] = float(profile["scale"]) + 0.70 * complexity
    profile["clahe"] = float(profile["clahe"]) + 2.20 * complexity
    profile["sharpen"] = float(profile["sharpen"]) + 0.85 * complexity
    profile["edges"] = float(profile["edges"]) + 0.28 * complexity
    return profile


def _enhance_detail(gray: np.ndarray, detail_idx: int) -> np.ndarray:
    profile = DETAIL_LEVELS[detail_idx % len(DETAIL_LEVELS)]
    enhanced = gray

    clahe_clip = float(profile["clahe"])
    if clahe_clip > 0:
        clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
        enhanced = clahe.apply(enhanced)

    sharpen_strength = float(profile["sharpen"])
    if sharpen_strength > 0:
        blurred = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
        enhanced = cv2.addWeighted(enhanced, 1.0 + sharpen_strength, blurred, -sharpen_strength, 0)

    edge_strength = float(profile["edges"])
    if edge_strength > 0:
        edges = cv2.Laplacian(enhanced, cv2.CV_16S, ksize=3)
        edges = cv2.convertScaleAbs(edges)
        enhanced = cv2.addWeighted(enhanced, 1.0, edges, edge_strength, 0)

    return enhanced


def _apply_profile(gray: np.ndarray, profile: dict[str, float | str]) -> np.ndarray:
    enhanced = gray

    clahe_clip = float(profile["clahe"])
    if clahe_clip > 0:
        clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
        enhanced = clahe.apply(enhanced)

    sharpen_strength = float(profile["sharpen"])
    if sharpen_strength > 0:
        blurred = cv2.GaussianBlur(enhanced, (0, 0), 1.1)
        enhanced = cv2.addWeighted(enhanced, 1.0 + sharpen_strength, blurred, -sharpen_strength, 0)

    edge_strength = float(profile["edges"])
    if edge_strength > 0:
        edges = cv2.Canny(enhanced, 60, 140)
        enhanced = cv2.addWeighted(enhanced, 1.0, edges, edge_strength, 0)

    return enhanced


def _render_rows_truecolor_rle(
    sampled: np.ndarray,
    chars: str,
    color_bgr: np.ndarray,   # (H, W, 3) uint8 — OpenCV BGR order
) -> str:
    """
    True-colour (24-bit) ultra path.  Groups adjacent pixels whose 4-bit-quantised
    colour and glyph match into a single run, then outputs the actual RGB value for
    the first pixel of each run.  This gives accurate colours (no ANSI-256 banding)
    with a similar escape-sequence count to the ANSI-256 path.
    """
    n = len(chars) - 1
    h, w = int(sampled.shape[0]), int(sampled.shape[1])
    rows: list[str] = []
    for row_idx in range(h):
        line     = sampled[row_idx]
        bgr_row  = color_bgr[row_idx]
        ch_idx   = np.clip(line.astype(np.int32) * n // 255, 0, n).astype(np.uint32)

        # 4-bit quantisation per channel (step 16) for span detection.
        # Pixels whose R, G, B all differ by < 16 share a run; actual RGB is output.
        rq = bgr_row[:, 2].astype(np.uint32) >> 4
        gq = bgr_row[:, 1].astype(np.uint32) >> 4
        bq = bgr_row[:, 0].astype(np.uint32) >> 4
        color_key = (rq << 8) | (gq << 4) | bq        # 12-bit, 0-4095
        keys = color_key * 256 + ch_idx

        if w == 0:
            rows.append("\033[0m")
            continue
        change = np.empty(w, dtype=bool)
        change[0] = True
        if w > 1:
            change[1:] = keys[1:] != keys[:-1]
        starts = np.flatnonzero(change)
        ends   = np.r_[starts[1:], w]
        parts: list[str] = []
        active_key = -1
        for si, ei in zip(starts, ends):
            key = int(keys[si])
            if key != active_key:
                r_val = int(bgr_row[si, 2])
                g_val = int(bgr_row[si, 1])
                b_val = int(bgr_row[si, 0])
                parts.append(f"\033[38;2;{r_val};{g_val};{b_val}m")
                active_key = key
            cch = chars[int(ch_idx[si])]
            run = ei - si
            parts.append(cch if run == 1 else cch * run)
        parts.append("\033[0m")
        rows.append("".join(parts))
    return "\n".join(rows)


def _render_rows_ultra_rle(
    sampled: np.ndarray,
    chars: str,
    color_codes: np.ndarray,
) -> str:
    """ANSI-256 ultra path: run-length encode identical (color, glyph) spans per row."""
    n = len(chars) - 1
    h, w = int(sampled.shape[0]), int(sampled.shape[1])
    rows: list[str] = []
    for row_idx in range(h):
        line = sampled[row_idx]
        code_row = color_codes[row_idx]
        ch_idx = np.clip(line.astype(np.int32) * n // 255, 0, n)
        keys = code_row.astype(np.uint32) * 256 + ch_idx.astype(np.uint32)
        if w == 0:
            rows.append("\033[0m")
            continue
        change = np.empty(w, dtype=bool)
        change[0] = True
        if w > 1:
            change[1:] = keys[1:] != keys[:-1]
        starts = np.flatnonzero(change)
        ends = np.r_[starts[1:], w]
        parts: list[str] = []
        active_code = -1
        for si, ei in zip(starts, ends):
            key = int(keys[si])
            code = key // 256
            chi = min(key % 256, n)
            if code != active_code:
                parts.append(_ANSI_FG[code])
                active_code = code
            cch = chars[chi]
            run = ei - si
            parts.append(cch if run == 1 else cch * run)
        parts.append("\033[0m")
        rows.append("".join(parts))
    return "\n".join(rows)


def _render_rows(
    sampled   : np.ndarray,
    chars     : str,
    color_ramp: list[str] | None,
    color_codes: np.ndarray | None = None,   # (H,W) uint8 ANSI-256 indices
) -> str:
    n = len(chars) - 1
    if color_codes is not None:
        return _render_rows_ultra_rle(sampled, chars, color_codes)

    rows: list[str] = []

    for line in sampled:
        if color_ramp:
            parts: list[str] = []
            active_color: str | None = None
            for pixel in line:
                pixel_int = int(pixel)
                color = color_ramp[pixel_int * (len(color_ramp) - 1) // 255]
                if color != active_color:
                    parts.append(color)
                    active_color = color
                parts.append(chars[pixel_int * n // 255])
            parts.append("\033[0m")
            rows.append("".join(parts))
        else:
            rows.append("".join(chars[int(pixel) * n // 255] for pixel in line))

    return "\n".join(rows)


def frame_to_ascii(
    frame,
    width: int,
    height: int,
    charset_idx: int,
    detail_idx: int = 0,
    auto_detail: bool = False,
    color_ramp: list[str] | None = None,
    color_frame=None,     # original BGR ndarray → triggers per-pixel ANSI-256 color
) -> str:
    chars = CHARSETS[charset_idx][0]

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    profile = _detail_profile(gray, detail_idx, auto_detail)
    # Ultra (color_frame): gentler local contrast / edges so ANSI color + gamma carry the look.
    if color_frame is not None:
        profile = dict(profile)
        profile["clahe"] = float(profile["clahe"]) * 0.88
        profile["sharpen"] = float(profile["sharpen"]) * 0.82
        profile["edges"] = float(profile["edges"]) * 0.75
    gray = _apply_profile(gray, profile)

    scale = float(profile["scale"])
    if color_frame is not None:
        # Slightly lower supersample than 2.35 — big CPU win with little visible loss at terminal res.
        scale = max(scale, 2.0)

    sample_w = max(width, int(width * scale))
    sample_h = max(height, int(height * scale))

    gh, gw = gray.shape[0], gray.shape[1]
    up = _UP if (sample_w > gw or sample_h > gh) else cv2.INTER_CUBIC
    # Downscale to cell grid: INTER_LINEAR is much faster than INTER_AREA at 1k+ wide ultra grids.
    down = cv2.INTER_LINEAR if (color_frame is not None and width * height >= 280_000) else cv2.INTER_AREA
    sampled = cv2.resize(gray, (sample_w, sample_h), interpolation=up)
    sampled = cv2.resize(sampled, (width, height), interpolation=down)
    if color_frame is not None:
        sampled = _gamma_u8(sampled, gamma=2.15)

    # Per-pixel colour path (Ultra mode).
    # Single-pass INTER_AREA downscale — faster and gives better averaging than
    # the old two-pass supersample; ANSI-256 cube is too coarse to benefit from it.
    if color_frame is not None:
        wcol = cv2.resize(color_frame, (width, height), interpolation=cv2.INTER_AREA)
        if _TRUECOLOR:
            return _render_rows_truecolor_rle(sampled, chars, wcol)
        codes = _compute_color_codes(wcol)
        return _render_rows(sampled, chars, None, codes)

    return _render_rows(sampled, chars, color_ramp)
