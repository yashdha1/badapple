"""Entry point for the terminal ASCII video player."""

import argparse
import os
import sys
import msvcrt

from player.download import download_video
from player.ui   import THEMES, draw_menu, scan_videos, video_full_path
from player.core import play


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--add", metavar="URL", help="Download a video into videos/ using yt-dlp")
    return parser.parse_args()


def show_menu(theme_idx: int) -> tuple[str, int]:
    os.system("cls")
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    videos = scan_videos()
    sel    = 0
    draw_menu(videos, sel, theme_idx)

    while True:
        ch = msvcrt.getch()

        if ch in (b"\xe0", b"\x00"):            # arrow keys
            arrow = msvcrt.getch()
            if videos:
                if arrow == b"H":               # ↑
                    sel = (sel - 1) % len(videos)
                elif arrow == b"P":             # ↓
                    sel = (sel + 1) % len(videos)
            draw_menu(videos, sel, theme_idx)

        elif ch in (b"\r", b"\n") and videos:   # ENTER → play selected
            sys.stdout.write("\033[?25h")
            return video_full_path(videos[sel]), theme_idx

        elif ch.lower() == b"p":                # custom path
            row = 9 + len(videos)
            sys.stdout.write(f"\033[?25h\033[{row};1H\033[2K  Enter video path: ")
            sys.stdout.flush()
            path = input().strip().strip('"')
            return path, theme_idx

        elif ch.lower() == b"t":
            theme_idx = (theme_idx + 1) % len(THEMES)
            draw_menu(videos, sel, theme_idx)

        elif ch.lower() == b"q":
            sys.stdout.write("\033[?25h\n")
            sys.exit(0)


def main() -> None:
    args = parse_args()
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
        video_path, theme_idx = show_menu(theme_idx)
        theme_idx = play(video_path, theme_idx)


if __name__ == "__main__":
    main()
