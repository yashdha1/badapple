"""Main playback loop - aspect-correct canvas, abs-clock A/V sync."""

import os
import sys
import time
import threading
import math
import random
from typing import NamedTuple

import cv2
import pygame

from .ascii  import DETAIL_LEVELS, frame_to_ascii, apply_letterbox, compute_canvas, CHARSETS, ULTRA_MAX_WIDTH
from .audio  import extract_audio, get_audio_duration
from .console_win import ConsoleWindowLock
from .input  import InputState, input_loop
from .modes import MODE_PRESETS
from .ui     import draw_hud, draw_loading, draw_video_only, theme_color_ramp, THEMES, \
                    make_audio_art, draw_audio_hud, next_video_in_library


def _pack_playback_frame(
    frame,
    asc_w: int,
    asc_h: int,
    pad_top: int,
    pad_left: int,
    container_rows: int,
    charset_idx: int,
    detail_idx: int,
    auto_detail: bool,
    color_ramp,
    color_frame,
) -> str:
    """Build letterboxed ASCII string (used by main playback; isolated for clarity)."""
    return apply_letterbox(
        frame_to_ascii(
            frame,
            asc_w,
            asc_h,
            charset_idx,
            detail_idx,
            auto_detail=auto_detail,
            color_ramp=color_ramp,
            color_frame=color_frame,
        ),
        pad_top,
        pad_left,
        asc_w,
        container_rows,
    )


class PlayResult(NamedTuple):
    theme_idx: int
    next_video: str | None = None


def _apply_mode_preset(state: InputState) -> None:
    preset = MODE_PRESETS.get(state.mode_name)
    if preset is None:
        return

    state.charset_idx = int(preset["charset_idx"]) % state.charset_count
    state.detail_idx = int(preset["detail_idx"]) % state.detail_count
    state.auto_detail = bool(preset["auto_detail"])
    state.colorized = bool(preset["colorized"])
    state.theme_idx = int(preset["theme_idx"]) % state.theme_count


def play(
    video_path: str,
    theme_idx: int = 0,
    *,
    seek_seconds: float = 5.0,
    end_mode: str = "next",
) -> PlayResult:
    if not os.path.exists(video_path):
        sys.stdout.write(f"\033[?25h\n  File not found: {video_path}\n")
        sys.stdout.flush()
        return PlayResult(theme_idx, None)

    title = os.path.basename(video_path)

    try:
        # OpenCV parallelizes resize/CLAHE; use most logical CPUs (override with OPENCV_NUM_THREADS).
        nt = int(os.environ.get("OPENCV_NUM_THREADS", "0") or "0")
        cv2.setNumThreads(nt if nt > 0 else max(4, (os.cpu_count() or 8)))
    except Exception:
        pass

    # -- video metadata (fast -- no extraction yet) --
    cap     = cv2.VideoCapture(video_path)
    fps     = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    vid_w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = (total_f / fps) if (fps > 0 and total_f > 0) else 0.0
    ss = max(0.1, float(seek_seconds))

    # -- lock terminal size while playing to avoid resize distortion --
    try:
        t = os.get_terminal_size()
        fixed_cols, fixed_rows = t.columns, t.lines
    except OSError:
        fixed_cols, fixed_rows = 120, 40

    console_lock = ConsoleWindowLock()
    console_lock.acquire(fixed_cols, fixed_rows)

    # -- canvas: correct AR + 16:9 letterbox --
    try:
        asc_w, asc_h, pad_top, pad_left, container_rows = compute_canvas(
            vid_w, vid_h, fixed_cols, fixed_rows, hud_rows=4
        )
    except OSError:
        asc_w, asc_h, pad_top, pad_left, container_rows = compute_canvas(
            vid_w, vid_h, fixed_cols, fixed_rows, hud_rows=4
        )

    # -- audio extraction (shows loading UI; skips when cached) --
    draw_loading(title, theme_idx)
    audio_path = extract_audio(video_path)
    has_audio  = audio_path is not None

    # -- pygame: small buffer = low audio latency --
    if has_audio:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        pygame.mixer.music.load(audio_path)

    # -- input state --
    state = InputState(
        charset_count=len(CHARSETS),
        detail_count=len(DETAIL_LEVELS),
        theme_count=len(THEMES),
        theme_idx=theme_idx,
    )

    os.system("cls")
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    t_input = threading.Thread(target=input_loop, args=(state,), daemon=True)
    t_input.start()

    def _compute_layout() -> tuple[int, int, int, int, int, int, int]:
        try:
            tc = os.get_terminal_size()
            term_cols, term_rows = tc.columns, tc.lines
        except OSError:
            term_cols, term_rows = fixed_cols, fixed_rows
        video_only = state.fullscreen or not state.hud_visible
        hud_rows = 0 if video_only else 4
        max_w = ULTRA_MAX_WIDTH if state.mode_name == "ultra" else None
        aw, ah, pt, pl, cr = compute_canvas(
            vid_w, vid_h,
            term_cols, term_rows,
            hud_rows=hud_rows,
            keep_cinematic_16_9=not video_only,
            max_width=max_w,
        )
        return aw, ah, pt, pl, cr, term_cols, term_rows

    def _render(frame, fn: int) -> None:
        nonlocal asc_w, asc_h, pad_top, pad_left, container_rows, fixed_cols, fixed_rows
        asc_w, asc_h, pad_top, pad_left, container_rows, fixed_cols, fixed_rows = _compute_layout()
        if state.colorized and state.mode_name == "ultra":
            color_ramp, color_frame = None, frame
        elif state.colorized:
            color_ramp, color_frame = theme_color_ramp(state.theme_idx), None
        else:
            color_ramp, color_frame = None, None
        af = _pack_playback_frame(
            frame,
            asc_w,
            asc_h,
            pad_top,
            pad_left,
            container_rows,
            state.charset_idx,
            state.detail_idx,
            state.auto_detail,
            color_ramp,
            color_frame,
        )

        if state.fullscreen or not state.hud_visible:
            draw_video_only(af)
            return

        draw_hud(
            af,
            fn,
            total_f,
            fps,
            container_rows,
            title,
            state.mode_name,
            state.charset_idx,
            detail_idx=state.detail_idx,
            auto_detail=state.auto_detail,
            colorized=state.colorized,
            theme_idx=state.theme_idx,
            paused=state.paused,
            term_cols=fixed_cols,
        )

    # -- pre-roll: decode first frame BEFORE starting clock/audio --
    ret, first_frame = cap.read()
    if not ret:
        cap.release()
        console_lock.release()
        return PlayResult(theme_idx, None)
    frame_num = 1
    _render(first_frame, frame_num)
    last_frame = first_frame
    last_frame_num = frame_num

    # Start clock and audio in lock-step
    playback_start = time.perf_counter()
    paused_at      = None
    if has_audio:
        pygame.mixer.music.play()

    # fps cap for ultra pixel mode (0 = no cap)
    frame_fps_cap: float = 0.0
    last_render_t: float = 0.0

    out_next: str | None = None

    # -- main playback loop --
    while cap.isOpened() and not state.quit:
        needs_refresh = state.redraw
        state.redraw = False

        if state.mode_changed:
            state.mode_changed = False
            _apply_mode_preset(state)
            preset      = MODE_PRESETS.get(state.mode_name, {})
            frame_fps_cap = float(preset.get("fps_cap") or 0)
            if preset.get("pixel_mode"):
                new_cols, new_rows = console_lock.fit_for_ultra(target_cols=ULTRA_MAX_WIDTH)
                fixed_cols = max(new_cols, 40)
                fixed_rows = max(new_rows, 20)
            elif preset.get("hd_mode"):
                new_cols, new_rows = console_lock.set_min_font_and_maximize(font_height=8)
                fixed_cols = max(new_cols, 40)
                fixed_rows = max(new_rows, 20)
            elif preset.get("restore_mode"):
                new_cols, new_rows = console_lock.restore_normal(font_height=16)
                fixed_cols = max(new_cols, 40)
                fixed_rows = max(new_rows, 20)
            last_render_t = 0.0
            os.system("cls")
            needs_refresh = True

        if state.fullscreen_toggle:
            state.fullscreen_toggle = False
            console_lock.set_maximized(state.fullscreen)
            try:
                t = os.get_terminal_size()
                fixed_cols, fixed_rows = t.columns, t.lines
            except OSError:
                pass
            last_render_t = 0.0
            os.system("cls")
            needs_refresh = True

        if state.hud_toggle:
            state.hud_toggle = False
            os.system("cls")
            needs_refresh = True

        # handle pause / resume
        if state.pause_toggle:
            state.pause_toggle = False
            needs_refresh = True
            if state.paused:
                paused_at = time.perf_counter()
                if has_audio:
                    pygame.mixer.music.pause()
            else:
                if paused_at is not None:
                    playback_start += time.perf_counter() - paused_at
                    paused_at = None
                if has_audio:
                    pygame.mixer.music.unpause()

        did_seek = False
        steps = state.seek_steps
        if steps != 0:
            state.seek_steps = 0
            delta_sec = steps * ss
            current_sec = min(last_frame_num / max(fps, 1e-9), duration_sec if duration_sec > 0 else 1e12)
            new_sec = current_sec + delta_sec
            if new_sec < 0:
                new_sec = 0
            if total_f > 0 and duration_sec > 0 and new_sec >= duration_sec - 1e-9:
                out_next = next_video_in_library(video_path)
                break
            target_idx = int(new_sec * fps)
            if total_f > 0:
                target_idx = min(max(0, target_idx), total_f - 1)
            else:
                target_idx = max(0, target_idx)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
            ret_s, f_seek = cap.read()
            if not ret_s or f_seek is None:
                out_next = next_video_in_library(video_path) if end_mode == "next" else None
                break
            frame_num = target_idx + 1
            last_frame_num = frame_num
            last_frame = f_seek
            new_sec = target_idx / max(fps, 1e-9)
            playback_start = time.perf_counter() - new_sec
            if state.paused:
                paused_at = time.perf_counter()
            if has_audio:
                pygame.mixer.music.stop()
                pygame.mixer.music.play(0, float(new_sec))
                if state.paused:
                    pygame.mixer.music.pause()
            needs_refresh = True
            last_render_t = 0.0
            did_seek = True

        if state.paused:
            if needs_refresh:
                _render(last_frame, last_frame_num)
            time.sleep(0.02)
            continue

        if not did_seek:
            ret, frame = cap.read()
            if not ret:
                if end_mode == "next":
                    out_next = next_video_in_library(video_path)
                break
            frame_num += 1

            # drift catch-up: skip frames if we have fallen behind
            elapsed  = time.perf_counter() - playback_start
            expected = int(elapsed * fps) + 1
            while frame_num < expected:
                ret2, frame2 = cap.read()
                if not ret2:
                    frame = None
                    break
                frame = frame2
                frame_num += 1
            if frame is None:
                if end_mode == "next":
                    out_next = next_video_in_library(video_path)
                break
        else:
            frame = last_frame

        now_r = time.perf_counter()
        should_draw = frame_fps_cap <= 0 or (now_r - last_render_t) >= 1.0 / frame_fps_cap
        if should_draw:
            _render(frame, frame_num)
            last_render_t = now_r
        last_frame = frame
        last_frame_num = frame_num

        # precise sleep to next frame boundary
        next_target = playback_start + frame_num / fps
        sleep       = next_target - time.perf_counter()
        if sleep > 0:
            time.sleep(sleep)

    # -- cleanup --
    state.quit = True
    cap.release()
    if has_audio:
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    console_lock.release()

    os.system("cls")
    if out_next is None:
        sys.stdout.write("\033[?25h\n  Playback ended. Press any key to return to menu...\n")
        sys.stdout.flush()
        import msvcrt
        msvcrt.getch()
    else:
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()
    return PlayResult(state.theme_idx, out_next)


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO-ONLY PLAYBACK
# ══════════════════════════════════════════════════════════════════════════════

def play_audio(audio_path: str, theme_idx: int = 0) -> int:
    """Play an audio file with animated spectrum-bar visualization."""
    if not os.path.exists(audio_path):
        sys.stdout.write(f"\033[?25h\n  File not found: {audio_path}\n")
        sys.stdout.flush()
        return theme_idx

    title = os.path.basename(audio_path)
    total_sec = get_audio_duration(audio_path)

    try:
        t = os.get_terminal_size()
        fixed_cols, fixed_rows = t.columns, t.lines
    except OSError:
        fixed_cols, fixed_rows = 120, 40

    console_lock = ConsoleWindowLock()
    console_lock.acquire(fixed_cols, fixed_rows)

    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
    pygame.mixer.music.load(audio_path)

    # Art dimensions: fill available terminal height
    art_rows = max(6, fixed_rows - 6)
    n_bars   = fixed_cols

    # Per-bar sine wave params for smooth animation
    phases = [random.uniform(0.0, 2 * math.pi) for _ in range(n_bars)]
    freqs  = [random.uniform(0.4, 3.5)         for _ in range(n_bars)]

    state = InputState(
        charset_count=1,
        detail_count=1,
        theme_count=len(THEMES),
        theme_idx=theme_idx,
    )

    t_input = threading.Thread(target=input_loop, args=(state,), daemon=True)
    t_input.start()

    os.system("cls")
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    pygame.mixer.music.play()
    start_time: float = time.perf_counter()
    paused_at : float | None = None

    while not state.quit:
        now = time.perf_counter()

        if state.pause_toggle:
            state.pause_toggle = False
            if state.paused:
                pygame.mixer.music.pause()
                paused_at = now
            else:
                pygame.mixer.music.unpause()
                if paused_at is not None:
                    start_time += now - paused_at
                    paused_at = None

        elapsed = (paused_at if paused_at is not None else now) - start_time
        elapsed = max(0.0, elapsed)

        if not state.paused and total_sec > 0 and elapsed >= total_sec:
            break

        # Animate: sine wave per bar, flatten bars when paused
        if state.paused:
            heights = [0.08] * n_bars
        else:
            heights = [
                0.5 + 0.48 * math.sin(freqs[i] * elapsed + phases[i])
                for i in range(n_bars)
            ]

        art = make_audio_art(fixed_cols, art_rows, heights, state.theme_idx)
        draw_audio_hud(art, elapsed, total_sec, title, state.paused, state.theme_idx, art_rows)

        time.sleep(1 / 20)

    state.quit = True
    pygame.mixer.music.stop()
    pygame.mixer.quit()
    console_lock.release()

    sys.stdout.write("\033[?25h\n  Playback ended. Press any key to return to menu...\n")
    sys.stdout.flush()
    import msvcrt
    msvcrt.getch()
    return state.theme_idx
