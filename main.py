"""Entry point for the terminal ASCII video player."""

import argparse
import os
import sys
import msvcrt

from player.download import download_video, download_audio
from player.ui   import THEMES, draw_menu, scan_videos, video_full_path, scan_audio, audio_full_path
from player.core import play, play_audio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--add", metavar="URL", help="Download a video into videos/ using yt-dlp")
    parser.add_argument("-a",    metavar="URL", help="Download audio-only into audio_extracted/ using yt-dlp")
    parser.add_argument(
        "--seek-seconds",
        type=float,
        default=5.0,
        metavar="SEC",
        help="Seconds to skip with ←/→ (default: 5)",
    )
    parser.add_argument(
        "--video-end",
        choices=("next", "menu"),
        default="next",
        help="When a video ends: play next file in videos/ (sorted), or return to menu (default: next)",
    )
    return parser.parse_args()


def show_menu(theme_idx: int) -> tuple[str, int, str]:
    """Return (path, theme_idx, kind) where kind is 'video' or 'audio'."""
    os.system("cls")
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    videos = scan_videos()
    audios = scan_audio()
    sel    = 0
    tab    = 0   # 0=videos  1=audio
    draw_menu(videos, sel, theme_idx, tab=tab, audio_files=audios)

    while True:
        ch = msvcrt.getch()

        if ch in (b"\xe0", b"\x00"):            # arrow keys
            arrow = msvcrt.getch()
            items = videos if tab == 0 else audios
            if items:
                if arrow == b"H":               # ↑
                    sel = (sel - 1) % len(items)
                elif arrow == b"P":             # ↓
                    sel = (sel + 1) % len(items)
            draw_menu(videos, sel, theme_idx, tab=tab, audio_files=audios)

        elif ch == b"\t":                       # TAB → switch tab
            tab = 1 - tab
            sel = 0
            draw_menu(videos, sel, theme_idx, tab=tab, audio_files=audios)

        elif ch in (b"\r", b"\n"):              # ENTER → play selected
            sys.stdout.write("\033[?25h")
            if tab == 0 and videos:
                return video_full_path(videos[sel]), theme_idx, "video"
            elif tab == 1 and audios:
                return audio_full_path(audios[sel]), theme_idx, "audio"

        elif ch.lower() == b"p":                # custom path
            row = 9 + len(videos)
            sys.stdout.write(f"\033[?25h\033[{row};1H\033[2K  Enter video path: ")
            sys.stdout.flush()
            path = input().strip().strip('"')
            return path, theme_idx, "video"

        elif ch.lower() == b"t":
            theme_idx = (theme_idx + 1) % len(THEMES)
            draw_menu(videos, sel, theme_idx, tab=tab, audio_files=audios)

        elif ch.lower() == b"q":
            sys.stdout.write("\033[?25h\n")
            sys.exit(0)


def main() -> None:
    args = parse_args()
    if args.a:
        try:
            saved_path = download_audio(args.a)
        except RuntimeError as exc:
            print(exc)
            raise SystemExit(1) from exc
        print(f"Audio saved to: {saved_path}")
        return

    if args.add:
        try:
            saved_path = download_video(args.add)
        except RuntimeError as exc:
            print(exc)
            raise SystemExit(1) from exc
        print(f"Downloaded to: {saved_path}")
        return

    theme_idx = 0
    while True:
        path, theme_idx, kind = show_menu(theme_idx)
        if kind == "audio":
            theme_idx = play_audio(path, theme_idx)
        else:
            while True:
                result = play(
                    path,
                    theme_idx,
                    seek_seconds=args.seek_seconds,
                    end_mode=args.video_end,
                )
                theme_idx = result.theme_idx
                if result.next_video:
                    path = result.next_video
                    continue
                break


if __name__ == "__main__":
    main()
