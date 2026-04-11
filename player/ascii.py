"""ASCII charset definitions, frame-to-ASCII conversion, and canvas math."""

import cv2
import numpy as np

CHARSETS: list[tuple[str, str]] = [
    (" .'`^\",;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$", "Detailed"),
    (" .,:;i1tfLCG08@",                                                          "Simple"),
    (" -+*#@",                                                                   "Minimal"),
    ("@%#*+=-:. ",                                                               "Inverse"),
    (" ░▒▓█",                                                                    "Block"),
    (" .oO0#",                                                                   "Soft Dot"),
    (" `.-:=+*#%@",                                                              "Gradient"),
    (" .,:irsXA253hMHGS#9B&@",                                                   "Retro"),
    (" _/|\\-=+*#%@",                                                            "Wire"),
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


def compute_canvas(
    vid_w: int,
    vid_h: int,
    term_cols: int,
    term_rows: int,
    hud_rows: int = _DEFAULT_HUD_ROWS,
    keep_cinematic_16_9: bool = True,
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

    # ── centering offsets ─────────────────────────────────────────────────────
    pad_top  = (container_rows - asc_h) // 2
    pad_left = (container_cols - asc_w) // 2

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


def _render_rows(sampled: np.ndarray, chars: str, color_ramp: list[str] | None) -> str:
    n = len(chars) - 1
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
) -> str:
    chars = CHARSETS[charset_idx][0]

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    profile = _detail_profile(gray, detail_idx, auto_detail)
    gray = _apply_profile(gray, profile)

    scale = float(profile["scale"])
    sample_w = max(width, int(width * scale))
    sample_h = max(height, int(height * scale))

    sampled = cv2.resize(gray, (sample_w, sample_h), interpolation=cv2.INTER_CUBIC)
    sampled = cv2.resize(sampled, (width, height), interpolation=cv2.INTER_AREA)
    return _render_rows(sampled, chars, color_ramp)
