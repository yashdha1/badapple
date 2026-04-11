"""Main playback loop - aspect-correct canvas, abs-clock A/V sync."""

import os
import sys
import time
import threading

import cv2
import pygame

from .ascii  import DETAIL_LEVELS, frame_to_ascii, apply_letterbox, compute_canvas, CHARSETS
from .audio  import extract_audio
from .console_win import ConsoleWindowLock
from .input  import InputState, input_loop
from .modes import MODE_PRESETS
from .ui     import draw_hud, draw_loading, draw_video_only, theme_color_ramp, THEMES


def _apply_mode_preset(state: InputState) -> None:
    preset = MODE_PRESETS.get(state.mode_name)
    if preset is None:
        return

    state.charset_idx = int(preset["charset_idx"]) % state.charset_count
    state.detail_idx = int(preset["detail_idx"]) % state.detail_count
    state.auto_detail = bool(preset["auto_detail"])
    state.colorized = bool(preset["colorized"])
    state.theme_idx = int(preset["theme_idx"]) % state.theme_count


def play(video_path: str, theme_idx: int = 0) -> int:
    if not os.path.exists(video_path):
        sys.stdout.write(f"\033[?25h\n  File not found: {video_path}\n")
        sys.stdout.flush()
        return theme_idx

    title = os.path.basename(video_path)

    # -- video metadata (fast -- no extraction yet) --
    cap     = cv2.VideoCapture(video_path)
    fps     = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    vid_w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

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

    def _compute_layout() -> tuple[int, int, int, int, int]:
        video_only = state.fullscreen or not state.hud_visible
        hud_rows = 0 if video_only else 4
        return compute_canvas(
            vid_w,
            vid_h,
            fixed_cols,
            fixed_rows,
            hud_rows=hud_rows,
            keep_cinematic_16_9=not video_only,
        )

    def _render(frame, fn: int) -> None:
        nonlocal asc_w, asc_h, pad_top, pad_left, container_rows
        asc_w, asc_h, pad_top, pad_left, container_rows = _compute_layout()
        color_ramp = theme_color_ramp(state.theme_idx) if state.colorized else None
        af = apply_letterbox(
            frame_to_ascii(
                frame,
                asc_w,
                asc_h,
                state.charset_idx,
                state.detail_idx,
                auto_detail=state.auto_detail,
                color_ramp=color_ramp,
            ),
            pad_top, pad_left, asc_w, container_rows,
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
        )

    # -- pre-roll: decode first frame BEFORE starting clock/audio --
    ret, first_frame = cap.read()
    if not ret:
        cap.release()
        console_lock.release()
        return state.theme_idx
    frame_num = 1
    _render(first_frame, frame_num)
    last_frame = first_frame
    last_frame_num = frame_num

    # Start clock and audio in lock-step
    playback_start = time.perf_counter()
    paused_at      = None
    if has_audio:
        pygame.mixer.music.play()

    # -- main playback loop --
    while cap.isOpened() and not state.quit:
        needs_refresh = state.redraw
        state.redraw = False

        if state.mode_changed:
            state.mode_changed = False
            _apply_mode_preset(state)
            os.system("cls")
            needs_refresh = True

        if state.fullscreen_toggle:
            state.fullscreen_toggle = False
            console_lock.set_maximized(state.fullscreen)
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

        if state.paused:
            if needs_refresh:
                _render(last_frame, last_frame_num)
            time.sleep(0.02)
            continue

        ret, frame = cap.read()
        if not ret:
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
            break

        _render(frame, frame_num)
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
    sys.stdout.write("\033[?25h\n  Playback ended. Press any key to return to menu...\n")
    sys.stdout.flush()

    import msvcrt
    msvcrt.getch()
    return state.theme_idx
