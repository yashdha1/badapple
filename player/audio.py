"""Audio extraction (ffmpeg) and playback (pygame)."""

import os
import sys

# All extracted audio is cached here so we never re-extract
AUDIO_CACHE_DIR = os.path.join("cache", "audio")


def _audio_path(video_path: str) -> str:
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_path))[0]
    return os.path.join(AUDIO_CACHE_DIR, base + ".mp3")


def extract_audio(video_path: str) -> str | None:
    """Return the cached audio path, extracting it with ffmpeg if needed."""
    path = _audio_path(video_path)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path

    sys.stdout.write("\n  Extracting audio (first run)…\n")
    sys.stdout.flush()
    code = os.system(
        f'ffmpeg -i "{video_path}" -q:a 0 -map a "{path}" -y -loglevel error 2>nul'
    )
    if code == 0 and os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    return None


def get_audio_duration(audio_path: str) -> float:
    """Return duration in seconds via ffprobe (fast, no decode)."""
    import subprocess
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0
