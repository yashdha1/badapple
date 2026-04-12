"""Video download helpers powered by yt-dlp."""

from __future__ import annotations

from pathlib import Path

VIDEOS_DIR = Path("videos")
AUDIO_DIR  = Path("audio_extracted")


def ensure_videos_dir() -> Path:
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    return VIDEOS_DIR


def ensure_audio_dir() -> Path:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIO_DIR


def download_video(url: str) -> str:
    """Download a video URL into videos/ and return the final path."""
    try:
        import yt_dlp
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "yt-dlp is not installed in the active project environment. "
            "Install it in .venv or run the project with the environment that has yt-dlp."
        ) from exc

    videos_dir = ensure_videos_dir()
    output_template = str(videos_dir / "%(title).120s [%(id)s].%(ext)s")

    options = {
        # cap 720p for better performance and compatibility, but allow audio+video merge if higher res is only available as separate streams. 
        "format": "bv*[height<=720]+ba/b[height<=720]",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "outtmpl": output_template,
        "restrictfilenames": False,
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        final_path = Path(ydl.prepare_filename(info))

        requested_ext = info.get("ext")
        merged_path = final_path.with_suffix(".mp4")
        if requested_ext and merged_path.exists() and final_path.suffix != ".mp4":
            return str(merged_path)
        if final_path.exists():
            return str(final_path)

    raise RuntimeError("Download finished but output file was not found.")


def download_audio(url: str) -> str:
    """Download audio-only from URL into audio_extracted/ as mp3."""
    try:
        import yt_dlp
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "yt-dlp is not installed in the active project environment."
        ) from exc

    audio_dir = ensure_audio_dir()
    output_template = str(audio_dir / "%(title).120s [%(id)s].%(ext)s")

    options = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "noplaylist": True,
        "outtmpl": output_template,
        "restrictfilenames": False,
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        raw_path = Path(ydl.prepare_filename(info))
        mp3_path = raw_path.with_suffix(".mp3")
        if mp3_path.exists():
            return str(mp3_path)
        candidates = sorted(
            audio_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if candidates:
            return str(candidates[0])

    raise RuntimeError("Audio download finished but output file was not found.")
