"""Video download helpers powered by yt-dlp."""

from __future__ import annotations

from pathlib import Path

VIDEOS_DIR = Path("videos")


def ensure_videos_dir() -> Path:
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    return VIDEOS_DIR


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
        "format": "bv*+ba/b",
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
