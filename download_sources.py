#!/usr/bin/env python3
"""
Download all source files needed by edit_decision_list.csv using yt-dlp.

Run this once before running make_showreel.py:
  python3 download_sources.py

Requirements:
  brew install yt-dlp
"""

from __future__ import annotations

import csv
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_DIR / "video-selection"
EDL_FILE = PROJECT_DIR / "edit_decision_list.csv"

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".webm", ".m4v")
AUDIO_EXTENSIONS = (".mp3", ".m4a", ".aac", ".flac", ".opus", ".ogg")
YOUTUBE_BASE = "https://www.youtube.com/watch?v="


def require_ytdlp() -> None:
    if shutil.which("yt-dlp") is None:
        raise SystemExit("yt-dlp not found. Install it with: brew install yt-dlp")


def already_exists(source_id: str, extensions: tuple[str, ...]) -> bool:
    return any(
        source_id in p.name and p.suffix.lower() in extensions
        for p in SOURCE_DIR.iterdir()
        if p.is_file()
    )


def download_video(source_id: str, hint: str) -> None:
    print(f"\n[VIDEO] {hint} ({source_id})")
    if already_exists(source_id, VIDEO_EXTENSIONS):
        print("  Already downloaded, skipping.")
        return
    subprocess.run([
        "yt-dlp",
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "-o", str(SOURCE_DIR / "%(title)s [%(id)s].%(ext)s"),
        YOUTUBE_BASE + source_id,
    ], check=True)


def download_audio(source_id: str, hint: str) -> None:
    print(f"\n[AUDIO] {hint} ({source_id})")
    if already_exists(source_id, AUDIO_EXTENSIONS):
        print("  Already downloaded, skipping.")
        return
    subprocess.run([
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "-o", str(SOURCE_DIR / "%(title)s [%(id)s].%(ext)s"),
        YOUTUBE_BASE + source_id,
    ], check=True)


def main() -> None:
    require_ytdlp()
    SOURCE_DIR.mkdir(exist_ok=True)

    needed: dict[str, dict] = defaultdict(lambda: {"types": set(), "hint": ""})
    with EDL_FILE.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source_id = row["source_id"].strip()
            item_type = row.get("type", "video").strip().lower()
            hint = row.get("source_hint", "").strip()
            needed[source_id]["types"].add(item_type)
            if not needed[source_id]["hint"]:
                needed[source_id]["hint"] = hint

    print(f"Found {len(needed)} unique sources to check.")
    for source_id, info in needed.items():
        if "video" in info["types"]:
            download_video(source_id, info["hint"])
        if "audio" in info["types"]:
            download_audio(source_id, info["hint"])

    print("\nDone. All sources are in video-selection/")


if __name__ == "__main__":
    main()
