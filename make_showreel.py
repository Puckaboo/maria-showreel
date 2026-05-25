#!/usr/bin/env python3
"""
Create a rough-cut showreel from an edit_decision_list.csv.

Source videos live in ./video-selection.
The script finds each video by its YouTube ID in the filename, cuts the listed
sections, normalizes format, and concatenates them in order into:
  ./output/maria_showreel_roughcut.mp4

Individual clips are written to ./work/ so you can inspect any single moment.

Requirements:
  - Python 3.9+
  - ffmpeg installed and available on PATH  (brew install ffmpeg)

─────────────────────────────────────────
NEXT STEPS (after the rough cut feels right)
─────────────────────────────────────────
1. Add a music bed
   - Pick one track (Jlin/HIIIT works well as the audio spine).
   - Set mute=yes on every row in edit_decision_list.csv.
   - Run this script again so all clips are silent.
   - Mix the music bed in with ffmpeg -i roughcut.mp4 -i music.mp3 ...
     or open the roughcut in any video editor and drop the track in.

2. Add short fades
   - Add a fade-in on the first clip and a fade-out on the last clip.
   - A simple ffmpeg vf "fade=t=in:st=0:d=0.5" on the first cut is enough.

3. Add a name card
   - Very minimal: just "Maria Martinez Paya", small text, first 3 seconds.
   - Use ffmpeg drawtext or add it in a video editor.

4. Experiment with cut timing
   - Once the music bed is in, trim individual start/end times in the CSV
     so cuts land on beats.  Re-run the script to regenerate instantly.
─────────────────────────────────────────
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_DIR / "video-selection"
WORK_DIR = PROJECT_DIR / "work"
OUTPUT_DIR = PROJECT_DIR / "output"
EDL_FILE = PROJECT_DIR / "edit_decision_list.csv"
OUTPUT_FILE = OUTPUT_DIR / "maria_showreel_roughcut.mp4"

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".webm", ".m4v")
AUDIO_EXTENSIONS = (".mp3", ".m4a", ".wav", ".aac", ".flac", ".opus", ".ogg")

# Output normalization. Change these if needed.
WIDTH = 1920
HEIGHT = 1080
FPS = 25
VIDEO_CRF = 18
AUDIO_BITRATE = "192k"


@dataclass(frozen=True)
class EditItem:
    type: str       # "video" or "audio"
    section: str
    source_id: str
    source_hint: str
    start: str
    end: str
    label: str
    mute: bool


def run(command: list[str]) -> None:
    print(" ".join(command))
    subprocess.run(command, check=True)


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit(
            "ffmpeg not found. Install it with: brew install ffmpeg"
        )


def read_edl() -> list[EditItem]:
    if not EDL_FILE.exists():
        raise SystemExit(f"Missing EDL file: {EDL_FILE}")

    items: list[EditItem] = []
    with EDL_FILE.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            items.append(
                EditItem(
                    type=row.get("type", "video").strip().lower(),
                    section=row["section"].strip(),
                    source_id=row["source_id"].strip(),
                    source_hint=row["source_hint"].strip(),
                    start=row["start"].strip(),
                    end=row["end"].strip(),
                    label=row["label"].strip(),
                    mute=row.get("mute", "no").strip().lower() in {"yes", "true", "1"},
                )
            )
    return items  # order is determined by row position in the file


def parse_seconds(timecode: str) -> float:
    """Parse HH:MM:SS or HH:MM:SS.d into a float number of seconds."""
    h, m, s = timecode.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def find_source_file(item_type: str, source_id: str, source_hint: str) -> Path:
    # Audio rows also search audio-only files; video rows stick to video formats.
    extensions = VIDEO_EXTENSIONS + AUDIO_EXTENSIONS if item_type == "audio" else VIDEO_EXTENSIONS
    candidates = [p for p in SOURCE_DIR.iterdir() if p.suffix.lower() in extensions]

    def prefer_format(paths: list[Path]) -> Path:
        if item_type == "audio":
            audio_files = [p for p in paths if p.suffix.lower() in AUDIO_EXTENSIONS]
            if audio_files:
                return sorted(audio_files)[0]
        mp4 = [p for p in paths if p.suffix.lower() == ".mp4"]
        return sorted(mp4)[0] if mp4 else sorted(paths)[0]

    id_matches = [p for p in candidates if source_id and source_id in p.name]
    if len(id_matches) == 1:
        return id_matches[0]
    if len(id_matches) > 1:
        return prefer_format(id_matches)

    hint_words = [word.lower() for word in source_hint.replace("_", " ").split() if len(word) >= 4]
    hint_matches = [p for p in candidates if all(word in p.name.lower() for word in hint_words[:2])]
    if len(hint_matches) == 1:
        return hint_matches[0]
    if len(hint_matches) > 1:
        return prefer_format(hint_matches)

    raise FileNotFoundError(
        f"Could not find source file for ID '{source_id}' / hint '{source_hint}'. "
        f"Put the file in ./video-selection and keep the YouTube ID in the filename."
    )


def cut_clip(item: EditItem, source: Path, index: int) -> Path:
    safe_section = "".join(ch if ch.isalnum() else "_" for ch in item.section).strip("_")
    safe_label = "".join(ch if ch.isalnum() else "_" for ch in item.label).strip("_")[:48]
    output = WORK_DIR / f"{index:03d}_{safe_section}_{safe_label}.mp4"

    # Re-encode every clip to identical technical parameters so concat is reliable.
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},format=yuv420p"
    )

    command = [
        "ffmpeg",
        "-y",
        "-ss", item.start,
        "-to", item.end,
        "-i", str(source),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", str(VIDEO_CRF),
    ]

    if item.mute:
        command += ["-an"]
    else:
        command += ["-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", "48000", "-ac", "2"]

    command.append(str(output))
    run(command)
    return output


def concatenate(clips: list[Path]) -> None:
    concat_file = WORK_DIR / "concat.txt"
    with concat_file.open("w", encoding="utf-8") as file:
        for clip in clips:
            file.write(f"file '{clip.resolve()}'\n")

    run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(OUTPUT_FILE),
    ])


def extract_audio(item: EditItem, source: Path, index: int) -> Path:
    """Extract an audio segment from source to a temp AAC file."""
    safe_label = "".join(ch if ch.isalnum() else "_" for ch in item.label).strip("_")[:48]
    output = WORK_DIR / f"{index:03d}_audio_{safe_label}.aac"
    run([
        "ffmpeg", "-y",
        "-ss", item.start,
        "-to", item.end,
        "-i", str(source),
        "-vn",
        "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", "48000", "-ac", "2",
        str(output),
    ])
    return output


def has_audio_stream(path: Path) -> bool:
    """Return True if the file contains at least one audio stream."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())


def mix_audio_beds(audio_beds: list[tuple[Path, float]]) -> None:
    """Overlay audio beds onto OUTPUT_FILE at the given timeline offsets (seconds).
    Replaces OUTPUT_FILE in-place.
    """
    video_has_audio = has_audio_stream(OUTPUT_FILE)

    inputs: list[str] = ["-i", str(OUTPUT_FILE)]
    for audio_path, _ in audio_beds:
        inputs += ["-i", str(audio_path)]

    filter_parts: list[str] = []
    audio_labels: list[str] = []
    for i, (_, offset_sec) in enumerate(audio_beds):
        delay_ms = int(offset_sec * 1000)
        label = f"[a{i + 1}]"
        filter_parts.append(f"[{i + 1}:a]adelay={delay_ms}|{delay_ms}{label}")
        audio_labels.append(label)

    if video_has_audio:
        all_inputs = ["[0:a]"] + audio_labels
        n = len(all_inputs)
        filter_parts.append(f"{''.join(all_inputs)}amix=inputs={n}:normalize=0[aout]")
    else:
        if len(audio_labels) == 1:
            filter_parts.append(f"{audio_labels[0]}anull[aout]")
        else:
            n = len(audio_labels)
            filter_parts.append(f"{''.join(audio_labels)}amix=inputs={n}:normalize=0[aout]")

    temp = OUTPUT_FILE.with_name("_temp_" + OUTPUT_FILE.name)
    run([
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        str(temp),
    ])
    temp.rename(OUTPUT_FILE)


def main() -> int:
    require_ffmpeg()
    SOURCE_DIR.mkdir(exist_ok=True)
    WORK_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    items = read_edl()
    video_clips: list[Path] = []
    audio_beds: list[tuple[Path, float]] = []  # (file, start offset in seconds)
    cumulative_video_seconds = 0.0

    print(f"Loaded {len(items)} edit decisions.")
    for i, item in enumerate(items):
        source = find_source_file(item.type, item.source_id, item.source_hint)
        print(f"\n[{i + 1:03d}] {item.type.upper()} | {item.section} - {item.label}")
        print(f"Source: {source.name}")

        if item.type == "video":
            video_clips.append(cut_clip(item, source, i + 1))
            cumulative_video_seconds += parse_seconds(item.end) - parse_seconds(item.start)
        elif item.type == "audio":
            audio_file = extract_audio(item, source, i + 1)
            audio_beds.append((audio_file, cumulative_video_seconds))
        else:
            print(f"  Warning: unknown type '{item.type}', skipping.")

    if not video_clips:
        raise SystemExit("No video clips in the edit list.")

    print("\nConcatenating video clips...")
    concatenate(video_clips)

    if audio_beds:
        print(f"\nMixing {len(audio_beds)} audio bed(s)...")
        mix_audio_beds(audio_beds)

    print(f"\nDone: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\nCommand failed with exit code {exc.returncode}", file=sys.stderr)
        raise
